"""Elasticsearch ``user_documents`` index: create, bulk index, delete by document."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from elasticsearch.helpers import bulk

from api.utils.elastic_chunk_index import (
    embed_documents_with_backpressure,
    embedding_from_env,
    get_elasticsearch_client,
)
from api.utils.logger import setup_logging
from api.utils.utils import get_uuid
from deepagent.core.text_splitters.user_document_split import UserDocumentChunk

logger = setup_logging()

USER_DOCUMENTS_INDEX = os.getenv("USER_DOCUMENTS_INDEX", "user_documents")
LEGAL_VECTOR_DIMS = int(os.getenv("LEGAL_VECTOR_DIMS", "1024"))
USER_DOC_ES_BULK_SIZE = max(50, int(os.getenv("USER_DOC_ES_BULK_SIZE", "200")))

_VECTOR_MAPPING: dict[str, Any] = {
    "type": "dense_vector",
    "dims": LEGAL_VECTOR_DIMS,
    "index": True,
    "similarity": "cosine",
}

USER_DOCUMENTS_MAPPING: dict[str, Any] = {
    "properties": {
        "chunk_id": {"type": "keyword"},
        "user_id": {"type": "keyword"},
        "kb_id": {"type": "keyword"},
        "document_id": {"type": "keyword"},
        "doc_title": {"type": "keyword"},
        "doc_type": {"type": "keyword"},
        "max_chunks": {"type": "integer"},
        "chunk_parent_id": {"type": "keyword"},
        "chunk_order": {"type": "integer"},
        "content_text": {"type": "text"},
        "content_vector": _VECTOR_MAPPING,
        "created_at": {"type": "date"},
    }
}


def ensure_user_documents_index(es=None) -> None:
    client = es or get_elasticsearch_client()
    if client.indices.exists(index=USER_DOCUMENTS_INDEX):
        return
    client.indices.create(index=USER_DOCUMENTS_INDEX, mappings=USER_DOCUMENTS_MAPPING)
    logger.info("Created Elasticsearch index={}", USER_DOCUMENTS_INDEX)


def delete_user_document_chunks(es, document_id: str) -> None:
    if not es.indices.exists(index=USER_DOCUMENTS_INDEX):
        return
    es.delete_by_query(
        index=USER_DOCUMENTS_INDEX,
        body={"query": {"term": {"document_id": document_id}}},
        refresh=True,
        conflicts="proceed",
    )


def index_user_document_chunks(
    *,
    user_id: str,
    kb_id: str,
    document_id: str,
    doc_title: str,
    doc_type: str,
    chunks: list[UserDocumentChunk],
    es=None,
) -> int:
    """Embed and bulk-index chunks; returns number of indexed documents."""
    if not chunks:
        return 0

    client = es or get_elasticsearch_client()
    ensure_user_documents_index(client)

    texts = [c.text for c in chunks]
    embeddings = embedding_from_env()
    vectors = embed_documents_with_backpressure(embeddings, texts)
    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"Embedding count mismatch: {len(vectors)} != {len(chunks)}"
        )

    now = datetime.utcnow().isoformat()
    actions: list[dict[str, Any]] = []
    for chunk, vector in zip(chunks, vectors):
        chunk_id = get_uuid()
        actions.append(
            {
                "_index": USER_DOCUMENTS_INDEX,
                "_id": chunk_id,
                "_source": {
                    "chunk_id": chunk_id,
                    "user_id": user_id,
                    "kb_id": kb_id or "",
                    "document_id": document_id,
                    "doc_title": doc_title[:512] if doc_title else "",
                    "doc_type": doc_type[:64] if doc_type else "",
                    "max_chunks": chunk.max_chunks,
                    "chunk_parent_id": chunk.chunk_parent_id or "",
                    "chunk_order": chunk.chunk_order,
                    "content_text": chunk.text,
                    "content_vector": vector,
                    "created_at": now,
                },
            }
        )

    success, errors = bulk(
        client,
        actions,
        chunk_size=USER_DOC_ES_BULK_SIZE,
        refresh="wait_for",
    )
    if errors:
        raise RuntimeError(f"Elasticsearch bulk failed: {errors[:3]}")
    logger.info(
        "Indexed user_documents document_id={} chunks={}",
        document_id,
        success,
    )
    return int(success)
