"""Parse documents from MinIO: Docling → chunk → embeddings → Elasticsearch."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from elasticsearch.helpers import bulk
from langchain_text_splitters import RecursiveCharacterTextSplitter

from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.apps.services.kb_service import KnowledgebaseService
from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio
from deepagent.core.providers.embeddings.base import create_embeddings
from deepagent.core.retrievers.base import build_elasticsearch_client, create_retriever

logger = setup_logging()

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


def _split_chunks(text: str) -> list[str]:
    size = int(os.getenv("LEX_CHUNK_SIZE", "1200"))
    overlap = int(os.getenv("LEX_CHUNK_OVERLAP", "200"))
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
    )
    parts = splitter.split_text(text)
    return [p for p in parts if p.strip()]


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
                "text": {"type": "text"},
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


def _bulk_index_vectors(
    es,
    index_name: str,
    *,
    document_id: str,
    kb_id: str,
    parse_type: str,
    chunks: list[str],
    vectors: list[list[float]],
) -> None:
    actions = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        actions.append(
            {
                "_op_type": "index",
                "_index": index_name,
                "_id": f"{document_id}_{i}",
                "_source": {
                    "text": chunk,
                    "vector": vec,
                    "document_id": document_id,
                    "kb_id": kb_id,
                    "chunk_index": i,
                    "parse_type": parse_type,
                },
            }
        )
    bulk(es, actions, refresh="wait_for")


def run_parse_document_job(document_id: str, parse_type: str = "docdealing") -> None:
    """Sync pipeline: load Document → MinIO → Docling → chunk → embed → ES. Updates ``progress`` on the row."""
    t0 = time.monotonic()
    index_name = os.getenv("ELASTIC_INDEX", "lex-companion-chunks")

    _set_progress(document_id, 0.02)
    ok, doc = DocumentService.get_by_id(document_id)
    if not ok or not doc:
        raise ValueError(f"Document not found: {document_id}")
    if _should_cancel(document_id):
        logger.info("parse job cancelled before start: %s", document_id)
        return

    file_row = FileService.get_or_none(id=doc.file_id)
    if not file_row or not file_row.location:
        raise ValueError(f"File missing for document {document_id}")

    kb = KnowledgebaseService.get_or_none(id=doc.kb_id)
    if not kb:
        raise ValueError(f"Knowledge base not found for document {document_id}")

    _set_progress(document_id, 0.08)

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
        # parse_type (e.g. docdealing): branch here for non-docling pipelines later
        text = _docling_to_markdown(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not (text or "").strip():
        raise RuntimeError("Docling produced empty text")

    _set_progress(document_id, 0.42)
    if _should_cancel(document_id):
        return

    chunks = _split_chunks(text)
    
    logger.info(f"Parse document: {document_id} chunks: {len(chunks)}")
    if not chunks:
        raise RuntimeError("No chunks after splitting")

    token_estimate = sum(len(c.split()) for c in chunks)
    _set_progress(document_id, 0.52, token_num=token_estimate)

    embeddings = _embedding_from_env()
    vectors = embeddings.embed_documents(chunks)
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
