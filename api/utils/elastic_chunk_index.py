"""Elasticsearch chunk index helpers shared by API import and parse worker."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from elasticsearch.helpers import bulk

from deepagent.core.providers.embeddings.base import create_embeddings
from deepagent.core.retrievers.base import build_elasticsearch_client
from api.utils.logger import setup_logging

logger = setup_logging()


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


def _normalize_embed_inputs(chunks: list[str]) -> list[str]:
    """Some providers drop empty strings; use a placeholder instead."""
    return [text if (text and str(text).strip()) else "." for text in chunks]


def _embed_batch_resilient(
    embeddings,
    batch: list[str],
    *,
    max_retries: int,
    retry_base_ms: int,
) -> list[list[float]]:
    """
    Embed one batch; if the API returns fewer vectors than inputs, fall back per item.

    OpenAI-compatible servers occasionally return partial batches (e.g. 5/8) without
    raising — that must not propagate or chunk↔vector pairs will be misaligned.
    """
    normalized = _normalize_embed_inputs(batch)
    attempt = 0
    while True:
        attempt += 1
        try:
            vectors = embeddings.embed_documents(normalized)
            break
        except Exception as e:
            msg = str(e)
            is_rate_limit = ("429" in msg) or ("rate_limit_error" in msg.lower())
            if (not is_rate_limit) or attempt >= max_retries:
                raise
            time.sleep((retry_base_ms * attempt) / 1000.0)

    if len(vectors) == len(normalized):
        return vectors

    logger.warning(
        "embed_documents returned {}/{} vectors for batch; retrying one-by-one",
        len(vectors),
        len(normalized),
    )
    one_by_one: list[list[float]] = []
    for text in normalized:
        item_vectors = embeddings.embed_documents([text])
        if len(item_vectors) != 1:
            raise RuntimeError(
                f"embed_documents returned {len(item_vectors)} vectors for a single input"
            )
        one_by_one.append(item_vectors[0])
    return one_by_one


def embed_documents_with_backpressure(embeddings, chunks: list[str]) -> list[list[float]]:
    batch_size = max(1, int(os.getenv("EMBEDDING_BATCH_SIZE", "8")))
    delay_ms = max(0, int(os.getenv("EMBEDDING_BATCH_DELAY_MS", "120")))
    max_retries = max(1, int(os.getenv("EMBEDDING_BATCH_MAX_RETRIES", "6")))
    retry_base_ms = max(100, int(os.getenv("EMBEDDING_RETRY_BASE_MS", "800")))

    all_vectors: list[list[float]] = []
    total = len(chunks)
    for start in range(0, total, batch_size):
        batch = chunks[start : start + batch_size]
        vectors = _embed_batch_resilient(
            embeddings,
            batch,
            max_retries=max_retries,
            retry_base_ms=retry_base_ms,
        )
        all_vectors.extend(vectors)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

    if len(all_vectors) != total:
        raise RuntimeError(
            f"Embedding count mismatch after resilient embed: {len(all_vectors)} != {total}"
        )
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


_DEFAULT_LEX_CHUNK_FIELDS = [
    "article_title^8",
    "subject_title^6",
    "topic_title^5",
    "content_text^2",
]

# Trường vector trong index — không trả về client.
_VECTOR_FIELD_NAMES = frozenset(
    {"content_vector", "vector", "embedding", "embeddings", "dense_vector"}
)

# Metadata chunk trả về API (không gồm vector).
_CHUNK_DOCUMENT_FIELDS = (
    "article_id",
    "topic_id",
    "topic_title",
    "topic_note",
    "subject_id",
    "subject_title",
    "source_subject",
    "article_title",
    "chapter_title",
    "source_note_text",
    "source_link",
    "related_note_text",
    "content_text",
    "max_chunks",
    "order",
    "parent_chunk_id",
    "created_at",
    "document_id",
    "doc_title",
    "doc_type",
    "chunk_order",
    "chunk_parent_id",
    "chunk_id",
    "user_id",
    "kb_id",
)


def strip_vector_fields(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    return {k: v for k, v in data.items() if k not in _VECTOR_FIELD_NAMES}


def normalize_score_0_1(score: Any) -> float | None:
    """
    Chuẩn hóa score về [0, 1] theo hàm đơn điệu:
      s <= 0 -> 0
      s > 0  -> s / (1 + s)
    Giữ được thứ tự xếp hạng, tránh mọi giá trị > 1.
    """
    if score is None:
        return None
    try:
        s = float(score)
    except (TypeError, ValueError):
        return None
    if s <= 0:
        return 0.0
    return round(s / (1.0 + s), 6)


def hit_to_api_chunk(hit: dict[str, Any], *, include_rerank: bool = False) -> dict[str, Any]:
    """Chuẩn hóa hit ES/rerank thành object phẳng cho response API (không vector)."""
    source = strip_vector_fields(dict(hit.get("_source") or {}))
    out: dict[str, Any] = {
        "chunk_id": hit.get("_id") or source.get("article_id"),
        "score": normalize_score_0_1(hit.get("_score")),
    }
    rerank_score = hit.get("rerank_score")
    if rerank_score is None:
        rerank_score = source.pop("rerank_score", None)
    if include_rerank and rerank_score is not None:
        out["rerank_score"] = rerank_score

    for field in _CHUNK_DOCUMENT_FIELDS:
        value = hit.get(field)
        if value is None:
            value = source.get(field)
        if value is not None:
            out[field] = value
    return out

_FIELD_BOOST_RE = re.compile(r"^(?P<field>[a-zA-Z0-9_.]+)(?:\^(?P<boost>\d+(?:\.\d+)?))?$")


def parse_weighted_fields(fields: list[str] | None) -> list[str]:
    """Normalize ES multi_match fields (``field`` or ``field^boost``)."""
    if not fields:
        return list(_DEFAULT_LEX_CHUNK_FIELDS)
    normalized: list[str] = []
    for raw in fields:
        text = (raw or "").strip()
        if not text:
            continue
        match = _FIELD_BOOST_RE.match(text)
        if not match:
            normalized.append(text)
            continue
        field = match.group("field")
        boost = match.group("boost")
        normalized.append(f"{field}^{boost}" if boost else field)
    return normalized or list(_DEFAULT_LEX_CHUNK_FIELDS)


class LexChunkSearch:
    """Hybrid keyword + vector search on ``lex_chunks_v1``."""

    def __init__(self, es=None, *, index_name: str | None = None) -> None:
        self.es = es or get_elasticsearch_client()
        self.index_name = index_name or os.getenv("LEX_CHUNKS_INDEX", "lex_chunks_v1")
        self._embeddings = None

    def _embeddings_client(self):
        if self._embeddings is None:
            self._embeddings = embedding_from_env()
        return self._embeddings

    def build_query_vector(self, query: str) -> list[float]:
        """Embed user query via configured local/OpenAI-compatible embedding server."""
        text = (query or "").strip()
        if not text:
            raise ValueError("query is required for vector search")
        vectors = embed_documents_with_backpressure(
            self._embeddings_client(),
            [text],
        )
        if not vectors:
            raise RuntimeError("Embedding server returned no vectors")
        return vectors[0]

    @staticmethod
    def _reference_filters(
        topic_ids: list[str] | None,
        subject_ids: list[str] | None,
    ) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = []
        if topic_ids:
            filters.append({"terms": {"topic_id": [str(t).strip() for t in topic_ids if str(t).strip()]}})
        if subject_ids:
            filters.append(
                {"terms": {"subject_id": [str(s).strip() for s in subject_ids if str(s).strip()]}}
            )
        return filters

    def build_search_query(
        self,
        *,
        query: str,
        query_vector: list[float],
        keyword_weight: float,
        fields: list[str],
        topic_ids: list[str] | None = None,
        subject_ids: list[str] | None = None,
        size: int,
    ) -> dict[str, Any]:
        """Build Elasticsearch body: keyword ``multi_match`` + ``knn`` on ``content_vector``."""
        kw = max(0.0, min(1.0, float(keyword_weight)))
        semantic_weight = 1.0 - kw
        filters = self._reference_filters(topic_ids, subject_ids)

        bool_query: dict[str, Any] = {"minimum_should_match": 0}
        should: list[dict[str, Any]] = []
        if kw > 0:
            mm: dict[str, Any] = {
                "query": query,
                "fields": fields,
                "type": "best_fields",
            }
            if kw != 1.0:
                mm["boost"] = kw
            should.append({"multi_match": mm})
        if should:
            bool_query["should"] = should
        if filters:
            bool_query["filter"] = filters

        body: dict[str, Any] = {
            "size": size,
            "_source": {"excludes": list(_VECTOR_FIELD_NAMES)},
        }
        if should or filters:
            body["query"] = {"bool": bool_query}
        else:
            body["query"] = {"match_all": {}}

        if semantic_weight > 0 and query_vector:
            knn: dict[str, Any] = {
                "field": "content_vector",
                "query_vector": query_vector,
                "k": size,
                "num_candidates": min(max(size * 2, size), 10_000),
                "boost": semantic_weight,
            }
            if filters:
                knn["filter"] = {"bool": {"filter": filters}}
            body["knn"] = knn

        return body

    @staticmethod
    def format_hits(response: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize ES hits for rerank / API response."""
        hits = (response or {}).get("hits", {}).get("hits", [])
        formatted: list[dict[str, Any]] = []
        for hit in hits:
            source = strip_vector_fields(hit.get("_source") or {})
            formatted.append(
                {
                    "_id": hit.get("_id"),
                    "_score": normalize_score_0_1(hit.get("_score")),
                    "_source": source,
                    "article_id": source.get("article_id"),
                    "topic_id": source.get("topic_id"),
                    "topic_title": source.get("topic_title"),
                    "subject_id": source.get("subject_id"),
                    "subject_title": source.get("subject_title"),
                    "article_title": source.get("article_title"),
                    "chapter_title": source.get("chapter_title"),
                    "content_text": source.get("content_text"),
                }
            )
        return formatted

    @staticmethod
    def apply_similarity_threshold(
        hits: list[dict[str, Any]],
        similarity_threshold: float,
    ) -> list[dict[str, Any]]:
        """Giữ hit có ``_score`` lớn hơn ``similarity_threshold`` (trước rerank)."""
        threshold = float(similarity_threshold)
        kept: list[dict[str, Any]] = []
        for hit in hits:
            score = hit.get("_score")
            if score is None:
                continue
            if float(score) > threshold:
                kept.append(hit)
        return kept

    def search(
        self,
        query: str,
        *,
        candidate_size: int = 100,
        similarity_threshold: float = 0.5,
        keyword_weight: float = 0.3,
        field_weights: list[str] | None = None,
        topic_ids: list[str] | None = None,
        subject_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search ``lex_chunks_v1`` with hybrid keyword + semantic scoring.

        ``field_weights``: ES fields like ``article_title^8`` (boost after ``^``).
        """
        text = (query or "").strip()
        if not text:
            raise ValueError("query is required")

        size = max(1, int(candidate_size))
        fields = parse_weighted_fields(field_weights)
        query_vector = self.build_query_vector(text)
        body = self.build_search_query(
            query=text,
            query_vector=query_vector,
            keyword_weight=keyword_weight,
            fields=fields,
            topic_ids=topic_ids,
            subject_ids=subject_ids,
            size=size,
        )
        logger.info(
            "LexChunkSearch: index={} size={} keyword_weight={} filters topic={} subject={}",
            self.index_name,
            size,
            keyword_weight,
            bool(topic_ids),
            bool(subject_ids),
        )
        response = self.es.search(index=self.index_name, body=body)
        results = self.format_hits(response)
        raw_count = len(results)
        results = self.apply_similarity_threshold(results, similarity_threshold)
        logger.info(
            "LexChunkSearch: threshold={} kept {}/{} hits",
            similarity_threshold,
            len(results),
            raw_count,
        )
        return results

    def retrieval_document(
        self,
        query: str,
        document_ids: list[str],
        *,
        user_documents_index: str | None = None,
        max_chunks: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Full-text search on ``user_documents`` for session uploads.

        Filters by ``document_id`` in ``document_ids`` (no vector search).
        Returns all matching chunks for those documents (sorted by document + order).
        """
        ids = [str(d).strip() for d in (document_ids or []) if str(d).strip()]
        if not ids:
            return []

        index = user_documents_index or os.getenv(
            "USER_DOCUMENTS_INDEX", "user_documents"
        )
        size = max_chunks if max_chunks is not None else max(
            100, int(os.getenv("USER_DOC_RETRIEVAL_MAX_CHUNKS", "10000"))
        )
        text = (query or "").strip()

        bool_query: dict[str, Any] = {
            "filter": [{"terms": {"document_id": ids}}],
            "minimum_should_match": 0,
        }
        if text:
            bool_query["should"] = [
                {
                    "multi_match": {
                        "query": text,
                        "fields": ["content_text", "doc_title^2"],
                        "type": "best_fields",
                    }
                }
            ]

        body: dict[str, Any] = {
            "size": size,
            "_source": {"excludes": list(_VECTOR_FIELD_NAMES)},
            "query": {"bool": bool_query},
            "sort": [
                {"document_id": "asc"},
                {"chunk_order": {"order": "asc", "missing": "_last"}},
            ],
        }

        logger.info(
            "LexChunkSearch.retrieval_document: index={} document_ids={} size={}",
            index,
            len(ids),
            size,
        )
        response = self.es.search(index=index, body=body)
        return self.format_user_document_hits(response)

    @staticmethod
    def format_user_document_hits(response: dict[str, Any]) -> list[dict[str, Any]]:
        hits = (response or {}).get("hits", {}).get("hits", [])
        formatted: list[dict[str, Any]] = []
        for hit in hits:
            source = strip_vector_fields(hit.get("_source") or {})
            formatted.append(
                {
                    "_id": hit.get("_id"),
                    "_score": normalize_score_0_1(hit.get("_score")),
                    "_source": source,
                    "document_id": source.get("document_id"),
                    "doc_title": source.get("doc_title"),
                    "doc_type": source.get("doc_type"),
                    "content_text": source.get("content_text"),
                    "chunk_order": source.get("chunk_order"),
                    "chunk_parent_id": source.get("chunk_parent_id"),
                    "chunk_id": source.get("chunk_id"),
                    "user_id": source.get("user_id"),
                    "kb_id": source.get("kb_id"),
                    "max_chunks": source.get("max_chunks"),
                }
            )
        return formatted
