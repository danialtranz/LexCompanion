"""Import Hugging Face datasets (e.g. phapdien) into legal PostgreSQL tables."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Any

from datasets import get_dataset_config_names, load_dataset, load_dataset_builder

from api.apps.services.legal_service import LegalIngestionJobService
from api.db.models import (
    DB,
    LegalArticle,
    LegalGlossary,
    LegalOntologySubject,
    LegalSubject,
    LegalTopic,
    LegalTreeNode,
)
from api.utils.logger import setup_logging

logger = setup_logging()

_DEFAULT_DATASET_CONFIG = "articles"
_DEFAULT_PREVIEW_SAMPLES = 20
_MAX_PREVIEW_SAMPLES = 100

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


_POSTGRES_BATCH_SIZE = int(os.getenv("HF_POSTGRES_BATCH_SIZE", "500"))

_ONTOLOGY_TOPICS_FIELDS = (
    "topic_id",
    "topic_number",
    "topic_title_vi",
    "topic_title_en",
    "topic_note",
    "article_count",
    "demuc_count",
)
_ONTOLOGY_SUBJECTS_FIELDS = (
    "topic_id",
    "topic_number",
    "topic_title_vi",
    "topic_title_en",
    "subject_id",
    "subject_title_vi",
    "subject_title_en",
    "article_count",
)
_SUBJECTS_FIELDS = (
    "subject_id",
    "topic_id",
    "topic_number",
    "topic_title",
    "subject_number",
    "subject_title",
    "source_url",
    "file_version",
    "fetch_status",
    "fetch_error",
    "scraped_at",
)
_TREE_NODES_FIELDS = ("node_id", "parent_id", "kind", "number", "title", "raw_text")
_GLOSSARY_FIELDS = ("category", "vi", "en", "note")
_ARTICLES_FIELDS = (
    "subject_id",
    "topic_id",
    "topic_number",
    "topic_title",
    "subject_number",
    "subject_title",
    "article_anchor",
    "article_title",
    "chapter_title",
    "source_note_text",
    "source_links",
    "related_note_text",
    "content_text",
    "content_char_len",
    "content_word_count",
    "source_url",
    "scraped_at",
)


def build_article_id(
    subject_id: str,
    article_anchor: str | None,
    article_title: str | None = None,
) -> str:
    """Mã tham chiếu ổn định cho Elasticsearch; không lưu trong PostgreSQL."""
    raw = f"{subject_id or ''}{article_anchor or ''}{article_title or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _article_row_fingerprint(row: dict[str, Any]) -> str:
    """Nhận diện row trùng hệt (~33 cặp trong corpus phapdien)."""
    parts = (
        row.get("subject_id"),
        row.get("article_anchor"),
        row.get("article_title"),
        row.get("source_url"),
        row.get("content_text"),
    )
    raw = "|".join(str(p or "") for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_source_links(value: Any) -> list[dict[str, Any]] | None:
    if not value:
        return None
    if not isinstance(value, (list, tuple)):
        return None
    links: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        links.append({"text": item.get("text"), "href": item.get("href")})
    return links or None


def _map_hf_rows(
    rows: list[dict[str, Any]],
    fields: tuple[str, ...],
    *,
    required_field: str | None = None,
    str_fields: frozenset[str] = frozenset(),
    json_fields: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    now = datetime.utcnow()
    out: list[dict[str, Any]] = []
    for row in rows:
        if required_field and not _as_text(row.get(required_field)):
            continue
        mapped: dict[str, Any] = {}
        for field in fields:
            value = row.get(field)
            if field in json_fields:
                mapped[field] = _normalize_source_links(value)
            elif field in str_fields:
                mapped[field] = _as_text(value)
            else:
                mapped[field] = value
        mapped["created_at"] = now
        mapped["updated_at"] = now
        out.append(mapped)
    return out


def _load_full_config(dataset_name: str, config: str) -> list[dict[str, Any]]:
    ds = load_dataset(dataset_name, config, split="train")
    return [dict(row) for row in ds]


def _bulk_insert(model, rows: list[dict[str, Any]], batch_size: int = _POSTGRES_BATCH_SIZE) -> int:
    if not rows:
        return 0
    with DB.atomic():
        for i in range(0, len(rows), batch_size):
            model.insert_many(rows[i : i + batch_size]).execute()
    return len(rows)


def _clear_legal_tables() -> None:
    with DB.atomic():
        LegalArticle.delete().execute()
        LegalOntologySubject.delete().execute()
        LegalTreeNode.delete().execute()
        LegalSubject.delete().execute()
        LegalTopic.delete().execute()
        LegalGlossary.delete().execute()


def _rows_from_ontology_topics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _map_hf_rows(rows, _ONTOLOGY_TOPICS_FIELDS)


def _rows_from_ontology_subjects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _map_hf_rows(rows, _ONTOLOGY_SUBJECTS_FIELDS)


def _rows_from_subjects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _map_hf_rows(
        rows,
        _SUBJECTS_FIELDS,
        required_field="subject_id",
        str_fields=frozenset({"scraped_at"}),
    )


def _rows_from_tree_nodes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _map_hf_rows(rows, _TREE_NODES_FIELDS, required_field="node_id")


def _rows_from_glossary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _map_hf_rows(rows, _GLOSSARY_FIELDS, required_field="vi")


def _rows_from_articles(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    now = datetime.utcnow()
    article_rows: list[dict[str, Any]] = []
    skipped_exact_duplicates = 0
    seen_fingerprints: set[str] = set()
    str_fields = frozenset({"scraped_at"})
    json_fields = frozenset({"source_links"})
    for row in rows:
        subject_id = _as_text(row.get("subject_id"))
        if not subject_id:
            continue
        fingerprint = _article_row_fingerprint(row)
        if fingerprint in seen_fingerprints:
            skipped_exact_duplicates += 1
            continue
        seen_fingerprints.add(fingerprint)
        mapped: dict[str, Any] = {}
        for field in _ARTICLES_FIELDS:
            value = row.get(field)
            if field in json_fields:
                mapped[field] = _normalize_source_links(value)
            elif field in str_fields:
                mapped[field] = _as_text(value)
            else:
                mapped[field] = value
        mapped["created_at"] = now
        mapped["updated_at"] = now
        article_rows.append(mapped)
    return article_rows, skipped_exact_duplicates


def resolve_dataset_version(dataset_name: str) -> str | None:
    try:
        builder = load_dataset_builder(dataset_name, "articles")
        version = getattr(builder.info, "version", None)
        if version:
            return str(version)
    except Exception:
        pass
    return None


@DB.connection_context()
def import_phapdien_to_postgres(
    *,
    dataset_name: str,
    job_id: int,
    finalize: bool = True,
) -> dict[str, Any]:
    """
    Tải toàn bộ config phapdien từ Hugging Face và ghi vào các bảng legal_*.
    Không ghi File, Document hay KB. Elasticsearch được sync ở worker sau bước này.
    """
    success_rows = 0
    failed_rows = 0
    total_rows = 0
    stats: dict[str, int] = {}

    try:
        logger.info(f"import_phapdien_to_postgres start job_id={job_id} dataset={dataset_name!r}")
        _clear_legal_tables()

        steps = [
            ("ontology_topics", LegalTopic, _rows_from_ontology_topics),
            ("ontology_subjects", LegalOntologySubject, _rows_from_ontology_subjects),
            ("subjects", LegalSubject, _rows_from_subjects),
            ("tree_nodes", LegalTreeNode, _rows_from_tree_nodes),
            ("ontology_glossary", LegalGlossary, _rows_from_glossary),
        ]

        for config, model, mapper in steps:
            raw_rows = _load_full_config(dataset_name, config)
            mapped = mapper(raw_rows)
            inserted = _bulk_insert(model, mapped)
            stats[config] = inserted
            total_rows += len(raw_rows)
            success_rows += inserted
            LegalIngestionJobService.update_progress(job_id, success_rows=success_rows, failed_rows=failed_rows)
            logger.info(f"import_phapdien job_id={job_id} config={config} inserted={inserted}")

        article_raw = _load_full_config(dataset_name, "articles")
        total_rows += len(article_raw)
        article_rows, skipped_dup = _rows_from_articles(article_raw)
        article_inserted = _bulk_insert(LegalArticle, article_rows)
        stats["articles"] = article_inserted
        stats["articles_skipped_exact_duplicate"] = skipped_dup
        if skipped_dup:
            logger.info(f"import_phapdien job_id={job_id} skipped exact duplicate articles={skipped_dup}")
        success_rows += article_inserted

        result = {
            "job_id": job_id,
            "dataset_name": dataset_name,
            "total_rows": total_rows,
            "success_rows": success_rows,
            "failed_rows": failed_rows,
            "stats": stats,
            "status": "completed",
        }
        if finalize:
            LegalIngestionJobService.mark_finished(
                job_id,
                status="completed",
                total_rows=total_rows,
                success_rows=success_rows,
                failed_rows=failed_rows,
            )
            logger.info(
                f"import_phapdien_to_postgres done job_id={job_id} "
                f"total_rows={total_rows} success_rows={success_rows}"
            )
        return result
    except Exception as exc:
        logger.error(f"import_phapdien_to_postgres failed job_id={job_id}: {exc}")
        LegalIngestionJobService.mark_finished(
            job_id,
            status="failed",
            total_rows=total_rows,
            success_rows=success_rows,
            failed_rows=failed_rows + 1,
            error_message=str(exc),
        )
        raise
