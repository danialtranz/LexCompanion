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

from deepagent.core.text_splitters.law_split import LawTextSplitter, LLMResponseValidationError
from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.apps.services.kb_service import KnowledgebaseService
from api.db.models import LexDocumentChunk, db
from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from deepagent.core.providers.embeddings.base import create_embeddings
from deepagent.core.providers.llms.base import create_chat_model
from deepagent.core.prompts.prompt import EXTRACT_LAW_REFERENCE_PROMPT
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


def _llm_from_env() -> BaseChatModel:
    kwargs: dict[str, Any] = {
        "api_key": os.getenv("OPENAI_API_KEY") or "",
        "base_url": _normalize_openai_base_url(os.getenv("OPENAI_BASE_URL")),
    }
    model = os.getenv("LLM_MODEL")
    if model:
        kwargs["model"] = model
    temperature = os.getenv("LLM_TEMPERATURE")
    if temperature:
        kwargs["temperature"] = float(temperature)
    max_tokens = os.getenv("LLM_MAX_TOKENS")
    if max_tokens:
        kwargs["max_tokens"] = int(max_tokens)
    timeout = os.getenv("LLM_TIMEOUT")
    if timeout:
        kwargs["timeout"] = int(timeout)
    return create_chat_model(provider="openai", **kwargs)


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


def _split_chunks(text_md: str, extract_llm: BaseChatModel) -> list[str]:
    splitter = LawTextSplitter(extract_llm=extract_llm)
    try:
        parts = splitter.split_text(text_md)
    except LLMResponseValidationError:
        logger.exception("LLM response validation failed during chunk splitting")
        raise
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


_REFERENCE_PATTERNS = [
    re.compile(r"\bquy\s*định\s*tại\b", flags=re.IGNORECASE),
    re.compile(r"\bquy\s*định\s*của\b", flags=re.IGNORECASE),
]

_QUY_DINH_TAI_RE = re.compile(r"quy\s*định\s*tại", flags=re.IGNORECASE)
_LAW_LEVEL_POINT_RE = re.compile(
    r"\b((?:các\s+)?điểm)\s+([^;,.\n]+?)(?=\s+(?:các\s+)?khoản|\s+(?:các\s+)?điều|\s+quy\s*định|\Z)",
    flags=re.IGNORECASE,
)
_LAW_LEVEL_CLAUSE_RE = re.compile(
    r"\b((?:các\s+)?khoản)\s+([^;,.\n]+?)(?=\s+(?:các\s+)?điều|\s+quy\s*định|\Z)",
    flags=re.IGNORECASE,
)
_LAW_LEVEL_ARTICLE_RE = re.compile(
    r"\b((?:các\s+)?điều)\s+([^;,.\n]+?)(?=\s+quy\s*định|\Z)",
    flags=re.IGNORECASE,
)
_INTERNAL_LUAT_NAY_RE = re.compile(r"luật\s+này", flags=re.IGNORECASE)
_INTERNAL_CUA_LUAT_NAY_RE = re.compile(r"của\s+luật\s+này", flags=re.IGNORECASE)
_EXTERNAL_LAW_RE = re.compile(
    r"\b(bộ\s+luật|luật)\s+(?!này\b)",
    flags=re.IGNORECASE,
)


def _split_reference_values(raw: str) -> list[str | int]:
    text = (raw or "").strip().lower()
    if not text or text == "này":
        return ["này"]
    values: list[str | int] = []
    for piece in re.split(r"\s*,\s*|\s+và\s+", text):
        token = piece.strip()
        if not token or token == "này":
            values.append("này")
            continue
        if token.isdigit():
            values.append(int(token))
            continue
        if len(token) == 1 and token.isalpha():
            values.append(token)
            continue
        return []
    return values or ["này"]


def _suffix_matches_internal(scope: str, suffix: str) -> bool:
    normalized = (suffix or "").strip().lower()
    if scope == "article":
        return bool(_INTERNAL_LUAT_NAY_RE.search(normalized))
    return bool(_INTERNAL_CUA_LUAT_NAY_RE.search(normalized))


def _is_external_law_target(suffix: str) -> bool:
    normalized = (suffix or "").strip()
    if _INTERNAL_LUAT_NAY_RE.search(normalized):
        return False
    return bool(_EXTERNAL_LAW_RE.search(normalized))


def _materialize_nay_tokens(
    parsed: dict[str, Any], chunk_data: dict[str, Any]
) -> dict[str, Any]:
    article = _normalize_int(chunk_data.get("article"))
    clause = _normalize_int(chunk_data.get("clause"))
    point = chunk_data.get("point")

    def _resolve(values: list[Any], current: Any) -> list[Any]:
        resolved: list[Any] = []
        for value in values:
            if value == "này":
                if current is None:
                    resolved.append("này")
                else:
                    resolved.append(current)
            else:
                resolved.append(value)
        return resolved

    return {
        **parsed,
        "articles": _resolve(parsed.get("articles") or [], article),
        "clauses": _resolve(parsed.get("clauses") or [], clause),
        "points": _resolve(parsed.get("points") or [], point),
    }


def _build_internal_law_ref(
    *,
    pattern: str,
    start: int,
    end: int,
    scope: str,
    articles: list[Any],
    clauses: list[Any],
    points: list[Any],
    window_text: str,
    source: str,
) -> dict[str, Any]:
    return {
        "ref_type": "internal",
        "pattern": pattern,
        "scope": scope,
        "articles": articles,
        "clauses": clauses,
        "points": points,
        "window_text": window_text,
        "start": start,
        "end": end,
        "source": source,
    }


def _parse_internal_quy_dinh_tai(prefix: str, suffix: str) -> dict[str, Any] | None:
    """Validate nested internal ref: điểm→khoản→điều→luật này or shorter chains."""
    tail = (prefix or "")[-180:]
    point_match = None
    for match in _LAW_LEVEL_POINT_RE.finditer(tail):
        point_match = match
    clause_match = None
    for match in _LAW_LEVEL_CLAUSE_RE.finditer(tail):
        clause_match = match
    article_match = None
    for match in _LAW_LEVEL_ARTICLE_RE.finditer(tail):
        article_match = match

    if point_match:
        if not clause_match or not article_match:
            return None
        if not (
            point_match.start() < clause_match.start() < article_match.start()
        ):
            return None
        if not _suffix_matches_internal("point", suffix):
            return None
        points = _split_reference_values(point_match.group(2))
        clauses = _split_reference_values(clause_match.group(2))
        articles = _split_reference_values(article_match.group(2))
        if not points or not clauses or not articles:
            return None
        return {
            "scope": "point",
            "articles": articles,
            "clauses": clauses,
            "points": points,
        }

    if clause_match:
        if not article_match or clause_match.start() >= article_match.start():
            return None
        if not _suffix_matches_internal("clause", suffix):
            return None
        clauses = _split_reference_values(clause_match.group(2))
        articles = _split_reference_values(article_match.group(2))
        if not clauses or not articles:
            return None
        return {
            "scope": "clause",
            "articles": articles,
            "clauses": clauses,
            "points": [],
        }

    if article_match:
        if clause_match or point_match:
            return None
        if not _suffix_matches_internal("article", suffix):
            return None
        articles = _split_reference_values(article_match.group(2))
        if not articles:
            return None
        return {
            "scope": "article",
            "articles": articles,
            "clauses": [],
            "points": [],
        }

    return None


def _parse_llm_law_reference_response(raw: str) -> list[dict[str, Any]]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("LLM law reference response must be a JSON array")
    refs: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        scope = (item.get("scope") or "").strip().lower()
        if scope not in {"article", "clause", "point"}:
            continue
        refs.append(
            {
                "scope": scope,
                "articles": item.get("articles") or [],
                "clauses": item.get("clauses") or [],
                "points": item.get("points") or [],
                "ref_type": "internal",
            }
        )
    return refs


def _resolve_law_reference_with_llm(
    content: str,
    extract_llm: BaseChatModel,
    chunk_data: dict[str, Any],
) -> list[dict[str, Any]]:
    chunk_context = {
        "article": chunk_data.get("article"),
        "clause": chunk_data.get("clause"),
        "point": chunk_data.get("point"),
    }
    prompt = (
        EXTRACT_LAW_REFERENCE_PROMPT.replace(
            "{{CHUNK_CONTEXT_JSON}}",
            json.dumps(chunk_context, ensure_ascii=False),
        ).replace("{{INPUT_TEXT}}", content)
    )
    response = extract_llm.invoke([HumanMessage(content=prompt)])
    raw = getattr(response, "content", str(response))
    llm_refs = _parse_llm_law_reference_response(raw)
    return [_materialize_nay_tokens(ref, chunk_data) for ref in llm_refs]


def _resolve_reference_for_law(
    content: str,
    extract_llm: BaseChatModel,
    chunk_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    text = content or ""
    chunk_data = chunk_data or {}
    if not _QUY_DINH_TAI_RE.search(text):
        return []

    refs: list[dict[str, Any]] = []
    llm_needed = False

    for match in _QUY_DINH_TAI_RE.finditer(text):
        start, end = match.start(), match.end()
        prefix = text[max(0, start - 180) : start]
        suffix = text[end : end + 80]
        window_text = text[max(0, start - 40) : end + 40]

        if _is_external_law_target(suffix):
            continue

        parsed = _parse_internal_quy_dinh_tai(prefix, suffix)
        if parsed:
            materialized = _materialize_nay_tokens(parsed, chunk_data)
            refs.append(
                _build_internal_law_ref(
                    pattern=match.group(0),
                    start=start,
                    end=end,
                    scope=materialized["scope"],
                    articles=materialized.get("articles") or [],
                    clauses=materialized.get("clauses") or [],
                    points=materialized.get("points") or [],
                    window_text=window_text,
                    source="rule",
                )
            )
            continue

        if _INTERNAL_LUAT_NAY_RE.search(suffix) or _INTERNAL_CUA_LUAT_NAY_RE.search(
            suffix
        ):
            llm_needed = True

    if llm_needed and extract_llm is not None:
        try:
            llm_refs = _resolve_law_reference_with_llm(content, extract_llm, chunk_data)
            for ref in llm_refs:
                refs.append(
                    _build_internal_law_ref(
                        pattern="quy định tại",
                        start=-1,
                        end=-1,
                        scope=ref["scope"],
                        articles=ref.get("articles") or [],
                        clauses=ref.get("clauses") or [],
                        points=ref.get("points") or [],
                        window_text=content[:200],
                        source="llm",
                    )
                )
        except Exception:
            logger.exception("LLM fallback failed for law reference extraction")

    logger.info("law refs: %s", refs)
    return refs


def _resolve_reference_for_decree(content: str, extract_llm: BaseChatModel) -> list[dict[str, Any]]:
    return _detect_reference_phrases(content, ref_type="decree")


def _resolve_reference_for_circular(content: str, extract_llm: BaseChatModel) -> list[dict[str, Any]]:
    return _detect_reference_phrases(content, ref_type="circular")


def resolve_reference(doc_type: str | None, chunk_data: dict[str, Any], extract_llm: BaseChatModel) -> list[dict[str, Any]]:
    normalized_doc_type = (doc_type or "").strip().lower()
    content = (chunk_data.get("content") or "").strip()

    if normalized_doc_type in {"luat", "luat_sua_doi"}:
        return _resolve_reference_for_law(content, extract_llm, chunk_data)
    if normalized_doc_type in {"nghi_dinh", "nghi_dinh_sua_doi"}:
        return _resolve_reference_for_decree(content, extract_llm)
    if normalized_doc_type in {"thong_tu", "thong_tu_sua_doi"}:
        return _resolve_reference_for_circular(content, extract_llm)
    return chunk_data.get("references") or []


def _build_chunk_row(
    document_id: str, raw_chunk: str, extract_llm: BaseChatModel
) -> dict[str, Any]:
    chunk_data = json.loads(raw_chunk)
    doc_type = chunk_data.get("doc_type")
    chunk_id = (chunk_data.get("chunk_id") or "").strip()
    if not chunk_id:
        chunk_id = f"{document_id}_{uuid.uuid4().hex[:8]}"
    resolved_references = resolve_reference(doc_type, chunk_data, extract_llm)

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


def _persist_chunks_to_postgres(
    document_id: str, chunks: list[str], extract_llm: BaseChatModel
) -> None:
    if not chunks:
        return

    rows: list[dict[str, Any]] = []
    for raw_chunk in chunks:
        try:
            rows.append(_build_chunk_row(document_id, raw_chunk, extract_llm))
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


def enqueue_chunk_persist(
    document_id: str, chunks: list[str], extract_llm: BaseChatModel
) -> None:
    def _runner() -> None:
        try:
            _persist_chunks_to_postgres(document_id, chunks, extract_llm)
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
    extract_llm = _llm_from_env()
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

    try:
        chunks = _split_chunks(text_md, extract_llm)
    except LLMResponseValidationError as exc:
        logger.error(
            "parse_document aborted: invalid LLM response doc_id=%s error=%s",
            document_id,
            exc,
        )
        raise RuntimeError(
            f"Invalid LLM response while parsing document {document_id}: {exc}"
        ) from exc
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
    enqueue_chunk_persist(document_id, chunks, extract_llm)
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
