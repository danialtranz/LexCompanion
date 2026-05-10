"""Parse documents from MinIO: Docling → chunk → embeddings → Elasticsearch."""

from __future__ import annotations

import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from elasticsearch.helpers import bulk
from markdownify import markdownify as md

from deepagent.core.text_splitters.law_split import LawTextSplitter
from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.apps.services.kb_service import KnowledgebaseService
from api.db.models import LexDocumentChunk, db
from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio
from deepagent.core.providers.embeddings.base import create_embeddings
from deepagent.core.retrievers.base import build_elasticsearch_client, create_retriever
import json
from enum import Enum

logger = setup_logging()


class SourceType(Enum):
    MINIO = "minio"
    WEB_SCRAPING = "url_scraping"

class RefType(Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"

_TYPE_ALIASES = {"parse_ducument": "parse_document"}

# Docling loads RapidOCR / torch weights once per process — reuse a single converter.
_docling_converter: Any = None
_docling_lock = threading.Lock()


def normalize_task_type(raw: str | None) -> str:
    t = (raw or "").strip().lower()
    return _TYPE_ALIASES.get(t, t)


def _elastic_url() -> str:
    raw = (os.getenv("ELASTIC_HOST") or "localhost:9200").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"http://{raw}"


def _elastic_credentials() -> tuple[str | None, str | None]:
    password = os.getenv("ELASTIC_PASSWORD") or None
    user = os.getenv("ELASTIC_USER") or None
    if password and not user:
        user = "elastic"
    return user, password


def _normalize_openai_base_url(url: str | None) -> str | None:
    """OpenAI client expects ``base_url`` ending with ``/v1`` (e.g. ``http://host:6501/v1``)."""
    if not url or not str(url).strip():
        return None
    u = str(url).strip().rstrip("/")
    if u.endswith("/v1"):
        return u
    return f"{u}/v1"


def _embedding_from_env():
    provider = os.getenv("EMBEDDING_PROVIDER", "localai")
    kwargs: dict = {
        "api_key": os.getenv("EMBEDDING_API_KEY") or "",
        "base_url": _normalize_openai_base_url(os.getenv("EMBEDDING_BASE_URL")),
        "max_retrys": int(os.getenv("EMBEDDING_MAX_RETRIES", "3")),
    }
    model = os.getenv("EMBEDDING_MODEL")
    if model:
        kwargs["model"] = model
    return create_embeddings(provider=provider, **kwargs)


def get_docling_converter() -> Any:
    """Lazily construct one ``DocumentConverter`` per process (thread-safe)."""
    global _docling_converter
    if _docling_converter is not None:
        return _docling_converter
    with _docling_lock:
        if _docling_converter is not None:
            return _docling_converter
        from docling.document_converter import DocumentConverter

        logger.info("Docling: building DocumentConverter (one-time, may load OCR models)...")
        t0 = time.perf_counter()
        _docling_converter = DocumentConverter()
        logger.info(f"Docling: converter ready in {time.perf_counter() - t0:.1f}s")
        return _docling_converter


def warmup_docling() -> None:
    """Preload Docling at server startup so the first queued job skips cold start."""
    if os.getenv("LEX_DOCLING_WARMUP", "1").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        logger.info("Docling warmup skipped (LEX_DOCLING_WARMUP disabled)")
        return
    get_docling_converter()


def _docling_to_markdown(path: Path) -> str:
    converter = get_docling_converter()
    result = converter.convert(path)
    return result.document.export_to_markdown()


def _split_chunks(text_md: str) -> list[str]:
    splitter = LawTextSplitter()
    parts = splitter.split_text(text_md)
    return [p for p in parts if p.strip()]


def _html_content_to_raw_text(html_content: str) -> tuple[str, str]:
    markdown_text = md(html_content or "", heading_style="ATX").strip()
    # Remove markdown heading prefixes (#, ##, ###, ...)
    return re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", markdown_text).strip(), markdown_text


def _embed_documents_with_backpressure(embeddings, chunks: list[str]) -> list[list[float]]:
    """
    Embed theo lô nhỏ để tránh dồn request lên embedding server/GPU.
    Khi gặp 429 thì đợi rồi retry, ưu tiên hoàn thành toàn bộ thay vì fail sớm.
    """
    batch_size = max(1, int(os.getenv("EMBEDDING_BATCH_SIZE", "8")))
    delay_ms = max(0, int(os.getenv("EMBEDDING_BATCH_DELAY_MS", "120")))
    max_retries = max(1, int(os.getenv("EMBEDDING_BATCH_MAX_RETRIES", "6")))
    retry_base_ms = max(100, int(os.getenv("EMBEDDING_RETRY_BASE_MS", "800")))

    all_vectors: list[list[float]] = []
    total = len(chunks)
    for start in range(0, total, batch_size):
        batch = chunks[start : start + batch_size]
        attempt = 0
        while True:
            attempt += 1
            try:
                vectors = embeddings.embed_documents(batch)
                all_vectors.extend(vectors)
                break
            except Exception as e:
                msg = str(e)
                is_rate_limit = ("429" in msg) or ("rate_limit_error" in msg.lower())
                if (not is_rate_limit) or attempt >= max_retries:
                    raise
                wait_ms = retry_base_ms * attempt
                logger.warning(
                    "Embedding 429 at batch %s-%s (attempt %s/%s), sleep %sms",
                    start,
                    min(start + batch_size, total),
                    attempt,
                    max_retries,
                    wait_ms,
                )
                time.sleep(wait_ms / 1000.0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
    return all_vectors


def _set_progress(document_id: str, progress: float, **fields) -> None:
    payload = {"progress": progress, **fields}
    DocumentService.update_by_id(document_id, payload)


def _should_cancel(document_id: str) -> bool:
    ok, doc = DocumentService.get_by_id(document_id)
    return bool(ok and doc and getattr(doc, "run", None) == "2")


def _ensure_chunk_index(es, index_name: str, dims: int) -> None:
    if es.indices.exists(index=index_name):
        return
    es.indices.create(
        index=index_name,
        mappings={
            "properties": {
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "doc_type": {"type": "keyword"},
                "law_name": {"type": "keyword"},
                "law_number": {"type": "keyword"},
                "issued_by": {"type": "keyword"},
                "signer": {"type": "keyword"},
                "status": {"type": "keyword"},
                "based_on": {"type": "keyword"},
                "implements": {"type": "keyword"},
                "replaces": {"type": "keyword"},
                "title_tks": {"type": "text", "analyzer": "standard"},
                "content_tks": {"type": "text", "analyzer": "standard"},
                "doc_name": {"type": "text", "analyzer": "standard"},
                "content": {"type": "text", "analyzer": "standard"},
                "content_md": {"type": "text"},
                "chapter": {"type": "integer"},
                "chapter_text": {"type": "keyword"},
                "article": {"type": "integer"},
                "article_text": {"type": "keyword"},
                "clause": {"type": "integer"},
                "clause_text": {"type": "keyword"},
                "point": {"type": "integer"},
                "point_text": {"type": "keyword"},
                "effective_date": {"type": "date"},
                "expiry_date": {"type": "date"},
                "amends": {
                    "type": "nested",
                    "properties": {
                        "target_doc": {"type": "keyword"},
                        "chapter": {"type": "integer"},
                        "article": {"type": "integer"},
                        "clause": {"type": "integer"},
                        "point": {"type": "keyword"},
                        "scope": {"type": "keyword"},
                        "action": {"type": "keyword"},
                    },
                },
                "vector": {
                    "type": "dense_vector",
                    "dims": dims,
                    "index": True,
                    "similarity": "cosine",
                },
                "document_id": {"type": "keyword"},
                "kb_id": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "parse_type": {"type": "keyword"},
                "full_path": {"type": "keyword"},
            }
        },
    )


def _delete_old_chunks(es, index_name: str, document_id: str) -> None:
    try:
        es.delete_by_query(
            index=index_name,
            query={"term": {"document_id": document_id}},
            conflicts="proceed",
            refresh=True,
        )
    except Exception as e:
        logger.warning("delete_by_query skipped or failed: %s", e)


def _normalize_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return None


_REFERENCE_PATTERNS = [
    re.compile(r"\bquy\s*định\s*tại\b", flags=re.IGNORECASE),
    re.compile(r"\bquy\s*định\s*của\b", flags=re.IGNORECASE),
]


def _detect_reference_phrases(content: str, ref_type: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for pattern in _REFERENCE_PATTERNS:
        for match in pattern.finditer(content or ""):
            refs.append(
                {
                    "ref_type": ref_type,
                    "pattern": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                }
            )
    return refs


def _resolve_reference_for_law(content: str) -> list[dict[str, Any]]:
    text = content or ""
    text_lower = text.lower()
    idx_tai = text_lower.find("quy định tại")
    idx_cua = text_lower.find("quy định của")

    # Bỏ qua nếu không có cụm nào, hoặc có đồng thời cả 2 cụm.
    if (idx_tai == -1 and idx_cua == -1) or (idx_tai != -1 and idx_cua != -1):
        return []

    refs: list[dict[str, Any]] = []

    if idx_tai != -1:
        # Dò tối đa 25 ký tự từ vị trí bắt đầu cụm "quy định tại".
        initial_window = text[idx_tai : idx_tai + 25]
        prefix = text[max(0, idx_tai - 120) : idx_tai]

        clause_tokens = re.findall(
            r"\bkhoản\s+([0-9]+|[a-zA-Z](?:\s*,\s*[a-zA-Z])*)\b",
            prefix,
            flags=re.IGNORECASE,
        )
        article_tokens = re.findall(
            r"\bđiều\s+([0-9]+(?:\s*,\s*[0-9]+)*)\b",
            prefix,
            flags=re.IGNORECASE,
        )
        point_tokens = re.findall(
            r"\bđiểm\s+([a-zA-Z](?:\s*,\s*[a-zA-Z])*)\b",
            prefix,
            flags=re.IGNORECASE,
        )

        clauses: list[str] = []
        for token in clause_tokens:
            pieces = [p.strip().lower() for p in token.split(",") if p.strip()]
            clauses.extend(pieces)

        articles: list[int] = []
        for token in article_tokens:
            for p in token.split(","):
                p = p.strip()
                if p.isdigit():
                    articles.append(int(p))
        points: list[str] = []
        for token in point_tokens:
            pieces = [p.strip().lower() for p in token.split(",") if p.strip()]
            points.extend(pieces)

        unique_clauses = list(dict.fromkeys(clauses))
        unique_articles = list(dict.fromkeys(articles))
        unique_points = list(dict.fromkeys(points))

        # Nếu có nhiều điều/khoản thì mở rộng cửa sổ dò lên 40 ký tự tiếp theo.
        need_extend = (
            len(unique_clauses) > 1
            or len(unique_articles) > 1
            or len(unique_points) > 1
        )
        scan_window = text[idx_tai : idx_tai + (40 if need_extend else 25)]
        scan_lower = scan_window.lower()
        has_cua = "của" in scan_lower
        has_nay = "này" in scan_lower

        close_enough = True
        if has_cua and has_nay:
            # Khoảng cách giữa "của" và "này" không quá 3 từ.
            words = re.findall(r"\S+", scan_window)
            pos_cua = next((i for i, w in enumerate(words) if w.lower() == "của"), None)
            pos_nay = next((i for i, w in enumerate(words) if w.lower() == "này"), None)
            if pos_cua is not None and pos_nay is not None:
                close_enough = abs(pos_cua - pos_nay) <= 4

        if (has_cua or has_nay) and close_enough and (
            unique_clauses or unique_articles or unique_points
        ):
            refs.append(
                {
                    "ref_type": "law",
                    "pattern": "quy định tại",
                    "clauses": unique_clauses,
                    "articles": unique_articles,
                    "points": unique_points,
                    "window_text": scan_window,
                    "start": idx_tai,
                    "end": idx_tai + len("quy định tại"),
                }
            )
        logger.info(f"refs: {refs}")
        return refs

    # Case "quy định của"
    idx_after = idx_cua + len("quy định của")
    tail = text[idx_after:]
    law_match = re.search(r"\bLuật\b", tail)
    if not law_match:
        return []

    law_start = idx_after + law_match.start()
    prev_20 = text[max(0, law_start - 20) : law_start].rstrip()
    if not prev_20.endswith(";"):
        return []

    semicolon_after = text.find(";", law_start)
    if semicolon_after == -1:
        return []

    law_name = text[law_start:semicolon_after].strip()
    refs.append(
        {
            "ref_type": "law",
            "pattern": "quy định của",
            "law_name": law_name,
            "start": idx_cua,
            "end": idx_cua + len("quy định của"),
        }
    )
    logger.info(f"refs: {refs}")
    return refs


def _resolve_reference_for_decree(content: str) -> list[dict[str, Any]]:
    return _detect_reference_phrases(content, ref_type="decree")


def _resolve_reference_for_circular(content: str) -> list[dict[str, Any]]:
    return _detect_reference_phrases(content, ref_type="circular")


def resolve_reference(doc_type: str | None, chunk_data: dict[str, Any]) -> list[dict[str, Any]]:
    normalized_doc_type = (doc_type or "").strip().lower()
    content = (chunk_data.get("content") or "").strip()

    if normalized_doc_type in {"luat", "luat_sua_doi"}:
        return _resolve_reference_for_law(content)
    if normalized_doc_type in {"nghi_dinh", "nghi_dinh_sua_doi"}:
        return _resolve_reference_for_decree(content)
    if normalized_doc_type in {"thong_tu", "thong_tu_sua_doi"}:
        return _resolve_reference_for_circular(content)
    return chunk_data.get("references") or []


def _build_chunk_row(document_id: str, raw_chunk: str) -> dict[str, Any]:
    chunk_data = json.loads(raw_chunk)
    doc_type = chunk_data.get("doc_type")
    chunk_id = (chunk_data.get("chunk_id") or "").strip()
    if not chunk_id:
        chunk_id = f"{document_id}_{uuid.uuid4().hex[:8]}"
    resolved_references = resolve_reference(doc_type, chunk_data)

    return {
        "id": uuid.uuid4().hex,
        "chunk_id": chunk_id,
        "doc_id": (chunk_data.get("doc_id") or document_id),
        "version_id": 1,
        "doc_type": doc_type,
        "law_number": chunk_data.get("law_number"),
        "law_name": chunk_data.get("law_name"),
        "issued_by": chunk_data.get("issued_by"),
        "signer": chunk_data.get("signer"),
        "status": chunk_data.get("status") or "active",
        "based_on": chunk_data.get("based_on") or [],
        "implements": chunk_data.get("implements") or [],
        "doc_name": chunk_data.get("doc_name"),
        "content_md": chunk_data.get("content"),
        "chapter": _normalize_int(chunk_data.get("chapter")),
        "chapter_text": chunk_data.get("chapter_text"),
        "article": _normalize_int(chunk_data.get("article")),
        "article_text": chunk_data.get("article_text"),
        "clause": _normalize_int(chunk_data.get("clause")),
        "clause_text": chunk_data.get("clause_text"),
        "point": _normalize_int(chunk_data.get("point")),
        "point_text": chunk_data.get("point_text"),
        "effective_date": chunk_data.get("effective_date"),
        "expiry_date": chunk_data.get("expiry_date"),
        "references": resolved_references,
        "amends": chunk_data.get("amends") or [],
    }


def _persist_chunks_to_postgres(document_id: str, chunks: list[str]) -> None:
    if not chunks:
        return

    rows: list[dict[str, Any]] = []
    for raw_chunk in chunks:
        try:
            rows.append(_build_chunk_row(document_id, raw_chunk))
        except Exception:
            logger.exception("Skip invalid chunk JSON while saving doc_id=%s", document_id)

    if not rows:
        logger.warning("No valid rows to save for doc_id=%s", document_id)
        return

    t0 = time.monotonic()
    with db.connection_context():
        LexDocumentChunk.delete().where(LexDocumentChunk.doc_id == document_id).execute()

        batch_size = max(100, int(os.getenv("LEX_CHUNK_DB_BATCH_SIZE", "500")))
        for i in range(0, len(rows), batch_size):
            LexDocumentChunk.insert_many(rows[i : i + batch_size]).execute()

    logger.info(
        "Saved %s chunks to postgres doc_id=%s in %.2fs",
        len(rows),
        document_id,
        time.monotonic() - t0,
    )


def enqueue_chunk_persist(document_id: str, chunks: list[str]) -> None:
    def _runner() -> None:
        try:
            _persist_chunks_to_postgres(document_id, chunks)
        except Exception:
            logger.exception("Background chunk persist failed doc_id=%s", document_id)

    threading.Thread(
        target=_runner,
        name=f"persist-chunks-{document_id[:8]}",
        daemon=True,
    ).start()


def _bulk_index_vectors(
    es,
    index_name: str,
    *,
    document_id: str,
    kb_id: str,
    parse_type: str,
    chunks: list[str],
    vectors: list[list[float]],
    content_md: str | None = None,
) -> None:
    actions = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        chunk_data = json.loads(chunk)
        content = (chunk_data.get("content") or "").strip()
        article = chunk_data.get("article")
        clause = chunk_data.get("clause")
        point = chunk_data.get("point", None)
        actions.append(
            {
                "_op_type": "index",
                "_index": index_name,
                "_id": chunk_data.get("chunk_id") or f"{document_id}_{i}",
                "_source": {
                    "doc_id": chunk_data.get("doc_id") or document_id,
                    "chunk_id": chunk_data.get("chunk_id") or f"{document_id}_{i}",
                    "doc_type": chunk_data.get("doc_type"),
                    "law_name": None,
                    "law_number": None,
                    "issued_by": None,
                    "signer": None,
                    "status": "active",
                    "based_on": [],
                    "implements": [],
                    "replaces": [],
                    "title_tks": chunk_data.get("article_text") or "",
                    "content_tks": content,
                    "doc_name": chunk_data.get("doc_name") or "",
                    "content": content,
                    "content_md": content_md or content,
                    "chapter": chunk_data.get("chapter"),
                    "chapter_text": chunk_data.get("chapter_text"),
                    "article": article,
                    "article_text": (
                        f"Điều {article}"
                        if article is not None
                        else (chunk_data.get("article_text") or None)
                    ),
                    "clause": clause,
                    "clause_text": f"Khoản {clause}" if clause is not None else None,
                    "point": chunk_data.get("point"),
                    "point_text": f"Điểm {point}" if point is not None else None,
                    "effective_date": None,
                    "expiry_date": None,
                    "amends": [],
                    "vector": vec,
                    "document_id": document_id,
                    "kb_id": kb_id,
                    "chunk_index": i,
                    "parse_type": parse_type,
                    "full_path": chunk_data.get("full_path") or "",
                },
            }
        )
    bulk(es, actions, refresh="wait_for")


def run_parse_document_job(document_id: str, parse_type: str = "docdealing") -> None:
    """Sync pipeline: load Document → MinIO → Docling → chunk → embed → ES. Updates ``progress`` on the row."""
    t0 = time.monotonic()
    index_name = os.getenv("ELASTIC_INDEX", "lex-companion-chunks")
    text_md: str | None = None

    _set_progress(document_id, 0.02)
    ok, doc = DocumentService.get_by_id(document_id)
    if not ok or not doc:
        raise ValueError(f"Document not found: {document_id}")
    if _should_cancel(document_id):
        logger.info("parse job cancelled before start: %s", document_id)
        return

    file_row = FileService.get_or_none(id=doc.file_id)
    if not file_row:
        raise ValueError(f"File missing for document {document_id}")

    kb = KnowledgebaseService.get_or_none(id=doc.kb_id)
    if not kb:
        raise ValueError(f"Knowledge base not found for document {document_id}")

    _set_progress(document_id, 0.08)

    source_type = (file_row.source_type or "").strip().lower()
    if source_type == SourceType.MINIO.value:
        if not file_row.location:
            raise ValueError(f"File location missing for document {document_id}")
        minio = LexCompanionMinio()
        raw = minio.get(kb.tenant_id, file_row.location)
        if raw is None:
            raise RuntimeError(f"MinIO get failed tenant={kb.tenant_id} key={file_row.location}")

        suffix = (doc.suffix or Path(file_row.name or "").suffix or ".bin").strip()
        if not suffix.startswith("."):
            suffix = f".{suffix}"

        _set_progress(document_id, 0.18)
        if _should_cancel(document_id):
            return

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = Path(tmp.name)

        try:
            text = _docling_to_markdown(tmp_path)
            text_md = text
        finally:
            tmp_path.unlink(missing_ok=True)
    elif source_type == SourceType.WEB_SCRAPING.value:
        html_content = (file_row.file_content or "").strip()
        if not html_content:
            raise ValueError(
                f"file_content is empty for non-minio source document {document_id}"
            )
        _set_progress(document_id, 0.18)
        if _should_cancel(document_id):
            return
        text, text_md = _html_content_to_raw_text(html_content)

    if not (text or "").strip():
        raise RuntimeError("Text extraction produced empty text")

    _set_progress(document_id, 0.42)
    if _should_cancel(document_id):
        return

    chunks = _split_chunks(text_md)
    # Ghi debug chunks vào đúng thư mục worker (không phụ thuộc cwd lúc chạy process).
    debug_chunks_file = Path(__file__).resolve().parent / f"chunks_{document_id}.txt"
    with debug_chunks_file.open("w", encoding="utf-8") as f:
        for idx, chunk in enumerate(chunks, start=1):
            f.write(f"===== CHUNK {idx} =====\n")
            f.write(f"{chunk}\n")
            try:
                chunk_obj = json.loads(chunk)
                content = (chunk_obj.get("content") or "").strip()
                f.write(f"content: {content}\n")
            except Exception:
                # Giữ debug resilient ngay cả khi chunk không phải JSON hợp lệ.
                pass
            f.write("\n")

    # Lưu chunks vào DB ở background thread để không block parse pipeline chính.
    enqueue_chunk_persist(document_id, chunks)
    logger.info(f"Wrote debug chunks file: {debug_chunks_file}")

    logger.info(f"Parse document: {document_id} chunks: {len(chunks)}")
    if not chunks:
        raise RuntimeError("No chunks after splitting")

    token_estimate = sum(len(c.split()) for c in chunks)
    _set_progress(document_id, 0.52, token_num=token_estimate)
    text_chunks = [(json.loads(c).get("content") or "").strip() for c in chunks]
    embeddings = _embedding_from_env()
    vectors = _embed_documents_with_backpressure(embeddings, text_chunks)
    if len(vectors) != len(chunks):
        raise RuntimeError("Embedding count does not match chunk count")

    dims = len(vectors[0])
    es_user, es_password = _elastic_credentials()
    es = build_elasticsearch_client(
        es_url=_elastic_url(),
        es_cloud_id=None,
        es_user=es_user,
        es_password=es_password,
        es_api_key=os.getenv("ELASTIC_API_KEY") or None,
    )

    _ensure_chunk_index(es, index_name, dims)
    _delete_old_chunks(es, index_name, document_id)

    _set_progress(document_id, 0.72)
    _bulk_index_vectors(
        es,
        index_name,
        document_id=document_id,
        kb_id=doc.kb_id,
        parse_type=parse_type,
        chunks=chunks,
        vectors=vectors,
        content_md=text_md,
    )

    _set_progress(document_id, 0.88)

    # create_retriever(
    #     provider="elasticsearch",
    #     index_name=index_name,
    #     body_func=lambda q: {"query": {"match": {"text": {"query": q}}}},
    #     content_field="text",
    #     client=es,
    # )

    elapsed = time.monotonic() - t0
    location_val = f"elasticsearch:{index_name}"
    _set_progress(
        document_id,
        1.0,
        chunk_num=len(chunks),
        token_num=token_estimate,
        process_duration=elapsed,
        location=location_val[:255],
    )

    if kb.vector_size == 0:
        KnowledgebaseService.update_by_id(kb.id, {"vector_size": dims})

    logger.info(
        "parse_document done doc_id=%s chunks=%s tokens~=%s index=%s",
        document_id,
        len(chunks),
        token_estimate,
        index_name,
    )
