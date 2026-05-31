"""Elasticsearch chunk index helpers shared by API import and parse worker."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from elasticsearch.helpers import bulk

from deepagent.core.providers.embeddings.base import create_embeddings
from deepagent.core.retrievers.base import build_elasticsearch_client


def elastic_url() -> str:
    raw = (os.getenv("ELASTIC_HOST") or "localhost:9200").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"http://{raw}"


def elastic_credentials() -> tuple[str | None, str | None]:
    password = os.getenv("ELASTIC_PASSWORD") or None
    user = os.getenv("ELASTIC_USER") or None
    if password and not user:
        user = "elastic"
    return user, password


def get_elasticsearch_client():
    es_user, es_password = elastic_credentials()
    return build_elasticsearch_client(
        es_url=elastic_url(),
        es_cloud_id=None,
        es_user=es_user,
        es_password=es_password,
        es_api_key=os.getenv("ELASTIC_API_KEY") or None,
    )


def normalize_openai_base_url(url: str | None) -> str | None:
    if not url or not str(url).strip():
        return None
    u = str(url).strip().rstrip("/")
    if u.endswith("/v1"):
        return u
    return f"{u}/v1"


def embedding_from_env():
    provider = os.getenv("EMBEDDING_PROVIDER", "localai")
    kwargs: dict = {
        "api_key": os.getenv("EMBEDDING_API_KEY") or "",
        "base_url": normalize_openai_base_url(os.getenv("EMBEDDING_BASE_URL")),
        "max_retrys": int(os.getenv("EMBEDDING_MAX_RETRIES", "3")),
    }
    model = os.getenv("EMBEDDING_MODEL")
    if model:
        kwargs["model"] = model
    return create_embeddings(provider=provider, **kwargs)


def embed_documents_with_backpressure(embeddings, chunks: list[str]) -> list[list[float]]:
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
                time.sleep((retry_base_ms * attempt) / 1000.0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
    return all_vectors


def ensure_chunk_index(es, index_name: str, dims: int) -> None:
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


def bulk_index_vectors(
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
                    "law_name": chunk_data.get("law_name"),
                    "law_number": chunk_data.get("law_number"),
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
