"""Import Hugging Face datasets (e.g. phapdien) into File, Document, and Elasticsearch."""

from __future__ import annotations

import json
import os
from typing import Any

from datasets import get_dataset_config_names, load_dataset, load_dataset_builder

from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.apps.services.kb_service import KnowledgebaseService
from api.db.models import Knowledgebase, Users
from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio
from api.utils.upload_preview import content_hash_xxhash128_hex
from api.utils.utils import get_uuid
from api.utils.elastic_chunk_index import (
    bulk_index_vectors,
    embed_documents_with_backpressure,
    embedding_from_env,
    ensure_chunk_index,
    get_elasticsearch_client,
)

logger = setup_logging()

_DEFAULT_DATASET_CONFIG = "articles"
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500
_DEFAULT_PREVIEW_SAMPLES = 20
_MAX_PREVIEW_SAMPLES = 100
_PARSE_TYPE = "hf_phapdien"

# tmquan/phapdien-moj-gov-vn — 6 bảng trên Hugging Face
PHAPDIEN_MOJ_CONFIG_META: dict[str, str] = {
    "articles": "Bảng chính: ~64k Điều pháp điển (toàn văn + metadata chủ đề/đề mục).",
    "subjects": "Siêu dữ liệu theo đề mục (subject): 202 dòng, URL nguồn, trạng thái crawl.",
    "tree_nodes": "Cây chủ đề / đề mục: 244 nút (topic → subject → …).",
    "ontology_topics": "42 chủ đề song ngữ Việt–Anh + số điều/đề mục.",
    "ontology_subjects": "202 đề mục song ngữ, gắn topic_id.",
    "ontology_glossary": "116 thuật ngữ pháp lý (category, vi, en).",
}

_PREVIEW_TEXT_TRUNCATE = 800


def _subject_title(row: dict[str, Any]) -> str | None:
    return (row.get("subject_title") or row.get("demuc_title") or "").strip() or None


def resolve_dataset_configs(dataset_name: str) -> list[str]:
    """Danh sách config HF; ưu tiên thứ tự đã biết cho phapdien."""
    try:
        names = list(get_dataset_config_names(dataset_name))
    except Exception:
        names = []
    if not names:
        return [_DEFAULT_DATASET_CONFIG]
    known = list(PHAPDIEN_MOJ_CONFIG_META.keys())
    ordered = [c for c in known if c in names]
    ordered.extend(c for c in names if c not in ordered)
    return ordered


def _json_safe_value(value: Any, *, max_str: int = _PREVIEW_TEXT_TRUNCATE) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) <= max_str:
            return value
        return value[:max_str] + f"... [{len(value)} chars total]"
    if isinstance(value, dict):
        return {k: _json_safe_value(v, max_str=max_str) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(v, max_str=max_str) for v in value]
    return str(value)[:max_str]


def _json_safe_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _json_safe_value(v) for k, v in row.items()}


def _config_total_rows(dataset_name: str, config: str) -> int | None:
    try:
        builder = load_dataset_builder(dataset_name, config)
        split = builder.info.splits.get("train")
        if split is not None and split.num_examples is not None:
            return int(split.num_examples)
    except Exception:
        pass
    return None


def preview_hf_dataset_all_configs(
    *,
    dataset_name: str,
    samples_per_config: int = _DEFAULT_PREVIEW_SAMPLES,
    configs: list[str] | None = None,
) -> dict[str, Any]:
    """
    Tải mẫu từ mọi config của dataset (mặc định 20 dòng/config) để khám phá schema.
    Không ghi MinIO, PostgreSQL hay Elasticsearch.
    """
    samples_per_config = max(1, min(samples_per_config, _MAX_PREVIEW_SAMPLES))
    config_list = configs or resolve_dataset_configs(dataset_name)
    results: list[dict[str, Any]] = []

    for config in config_list:
        split = f"train[:{samples_per_config}]"
        try:
            ds = load_dataset(dataset_name, config, split=split)
            rows = [_json_safe_row(dict(row)) for row in ds]
            columns = list(ds.features.keys()) if ds.features else (
                list(rows[0].keys()) if rows else []
            )
            total_rows = _config_total_rows(dataset_name, config)
            err = None
        except Exception as exc:
            rows = []
            columns = []
            total_rows = None
            err = str(exc)
            logger.error(f"preview config={config} failed: {exc}")

        results.append(
            {
                "config": config,
                "description": PHAPDIEN_MOJ_CONFIG_META.get(config),
                "total_rows": total_rows,
                "columns": columns,
                "sample_count": len(rows),
                "samples": rows,
                "error": err,
            }
        )

    return {
        "dataset_name": dataset_name,
        "config_count": len(config_list),
        "configs": config_list,
        "samples_per_config": samples_per_config,
        "tables": results,
    }


def _normalize_anchor(anchor: str | None) -> str:
    raw = (anchor or "").strip()
    if raw.startswith("#"):
        return raw[1:]
    return raw


def _build_article_body(row: dict[str, Any]) -> str:
    parts: list[str] = []
    chapter = (row.get("chapter_title") or "").strip()
    title = (row.get("article_title") or "").strip()
    content = (row.get("content_text") or "").strip()
    source_note = (row.get("source_note_text") or "").strip()
    if chapter:
        parts.append(chapter)
    if title:
        parts.append(title)
    if content:
        parts.append(content)
    if source_note:
        parts.append(f"\n[Nguồn] {source_note}")
    return "\n\n".join(parts).strip()


def _load_dataset_slice(
    dataset_name: str,
    *,
    config: str,
    offset: int,
    limit: int,
) -> list[dict[str, Any]]:
    end = offset + limit
    split = f"train[{offset}:{end}]"
    ds = load_dataset(dataset_name, config, split=split)
    return [dict(row) for row in ds]


def _index_article_to_elasticsearch(
    *,
    es,
    index_name: str,
    document_id: str,
    kb_id: str,
    body: str,
    row: dict[str, Any],
) -> int:
    anchor = _normalize_anchor(row.get("article_anchor"))
    chunk_id = anchor or f"{document_id}_0"
    chunk_payload = {
        "content": body,
        "doc_id": document_id,
        "chunk_id": chunk_id,
        "doc_name": (row.get("article_title") or "")[:255],
        "doc_type": "phapdien",
        "chapter_text": row.get("chapter_title"),
        "article_text": row.get("article_title"),
        "law_number": anchor[:64] if anchor else None,
        "law_name": (_subject_title(row) or "")[:255] or None,
        "full_path": row.get("source_url") or "",
    }
    chunk_json = json.dumps(chunk_payload, ensure_ascii=False)
    embeddings = embedding_from_env()
    vectors = embed_documents_with_backpressure(embeddings, [body])
    dims = len(vectors[0])
    ensure_chunk_index(es, index_name, dims)
    bulk_index_vectors(
        es,
        index_name,
        document_id=document_id,
        kb_id=kb_id,
        parse_type=_PARSE_TYPE,
        chunks=[chunk_json],
        vectors=vectors,
        content_md=body,
    )
    return dims


def import_hf_dataset_batch(
    *,
    user: Users,
    kb: Knowledgebase,
    dataset_name: str,
    config: str = _DEFAULT_DATASET_CONFIG,
    offset: int = 0,
    limit: int = _DEFAULT_LIMIT,
    skip_existing: bool = True,
) -> dict[str, Any]:
    """
    Tải một lô bản ghi từ HF, lưu MinIO + file/document + Elasticsearch.
    Gọi nhiều lần với offset tăng dần để import toàn bộ corpus lớn.
    """
    limit = max(1, min(limit, _MAX_LIMIT))
    offset = max(0, offset)
    index_name = os.getenv("ELASTIC_INDEX", "lex-companion-chunks")
    es = get_elasticsearch_client()
    minio = LexCompanionMinio()

    rows = _load_dataset_slice(dataset_name, config=config, offset=offset, limit=limit)
    imported = 0
    skipped_empty = 0
    skipped_duplicate = 0
    failed = 0
    document_ids: list[str] = []
    vector_dims: int | None = None

    for row in rows:
        body = _build_article_body(row)
        if not body:
            skipped_empty += 1
            continue

        anchor = _normalize_anchor(row.get("article_anchor"))
        content_hash = content_hash_xxhash128_hex(
            (anchor or body).encode("utf-8")
        )
        if skip_existing and DocumentService.get_active_by_kb_and_content_hash(
            kb.id, content_hash
        ):
            skipped_duplicate += 1
            continue

        try:
            body_bytes = body.encode("utf-8")
            file_id = get_uuid()
            doc_id = get_uuid()
            display_name = ((row.get("article_title") or anchor or "article")[:250]).strip()
            if not display_name.endswith(".txt"):
                file_name = f"{display_name}.txt"
            else:
                file_name = display_name

            object_key = f"{kb.id}/{file_id}.txt"
            put_res = minio.put(kb.tenant_id, object_key, body_bytes)
            if put_res is None:
                failed += 1
                continue

            file_row = FileService.save(
                id=file_id,
                tenant_id=kb.tenant_id,
                created_by=user.id,
                name=file_name[:255],
                location=object_key,
                file_content=body,
                size=len(body_bytes),
                type="txt",
                source_type="huggingface",
            )

            dims = _index_article_to_elasticsearch(
                es=es,
                index_name=index_name,
                document_id=doc_id,
                kb_id=kb.id,
                body=body,
                row=row,
            )
            vector_dims = dims

            DocumentService.save(
                id=doc_id,
                kb_id=kb.id,
                file_id=file_row.id,
                source_type="huggingface",
                type="txt",
                created_by=user.id,
                name=file_name[:255],
                location=f"elasticsearch:{index_name}"[:255],
                size=len(body_bytes),
                token_num=int(row.get("content_word_count") or 0),
                chunk_num=1,
                progress=1.0,
                process_duration=0.0,
                suffix=".txt",
                content_hash=content_hash,
                run="0",
                status="1",
                doc_type="phapdien",
                law_number=(anchor[:255] if anchor else None),
                law_name=(_subject_title(row) or "")[:255] or None,
            )
            imported += 1
            document_ids.append(doc_id)
        except Exception as exc:
            failed += 1
            logger.error(f"hf import row failed anchor={anchor!r}: {exc}")

    if imported and vector_dims:
        KnowledgebaseService.update_by_id(
            kb.id,
            {
                "doc_num": (kb.doc_num or 0) + imported,
                "chunk_num": (kb.chunk_num or 0) + imported,
                "vector_size": vector_dims if not kb.vector_size else kb.vector_size,
            },
        )

    return {
        "dataset_name": dataset_name,
        "config": config,
        "offset": offset,
        "limit": limit,
        "fetched": len(rows),
        "imported": imported,
        "skipped_empty": skipped_empty,
        "skipped_duplicate": skipped_duplicate,
        "failed": failed,
        "document_ids": document_ids,
        "kb_id": kb.id,
        "elastic_index": index_name,
        "next_offset": offset + len(rows),
    }
