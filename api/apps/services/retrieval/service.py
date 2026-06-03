"""Admin legal corpus retrieval: ES hybrid search -> rerank -> LLM answer."""

from __future__ import annotations

from typing import Any

from api.apps.services.chat_service import ChatSessionService
from api.utils.elastic_chunk_index import LexChunkSearch
from api.utils.logger import setup_logging
from deepagent.core.rerank.rerank import BgeM3Reranker, get_reranker, is_reranker_ready

from .citations import build_references
from .context import chunks_to_context, should_end_conversation
from .llm import generate_answer_with_citations
from .session import (
    merge_unique_ids,
    normalize_id_list,
    normalize_session_id,
    resolve_session_retrieval,
    session_blocked_message,
)

logger = setup_logging()


def rerank_hits(
    query: str,
    hits: list[dict[str, Any]],
    *,
    final_size: int,
    reranker: BgeM3Reranker | None = None,
) -> list[dict[str, Any]]:
    if not hits:
        return []
    limit = max(1, int(final_size))
    if reranker is not None:
        return reranker.rerank(
            query,
            hits,
            top_k=limit,
            text_field="content_text",
            include_titles=True,
        )
    if is_reranker_ready():
        return get_reranker().rerank(
            query,
            hits,
            top_k=limit,
            text_field="content_text",
            include_titles=True,
        )
    logger.warning("Reranker not ready; returning top hits by ES score")
    return hits[:limit]


def admin_retrieve_and_answer(
    *,
    query: str,
    session_id: str | None = None,
    user_id: str | None = None,
    candidate_size: int = 100,
    similarity_threshold: float = 0.5,
    final_size: int = 5,
    keyword_weight: float = 0.3,
    field_weights: list[str] | None = None,
    topic_ids: list[str] | None = None,
    subject_ids: list[str] | None = None,
    extra_doc_ids: list[str] | None = None,
    reranker: BgeM3Reranker | None = None,
) -> dict[str, Any]:
    """Run search -> rerank -> LLM; trả về query, answer (có [n]), reference (chỉ nguồn đã trích)."""
    blocked = session_blocked_message(session_id, user_id=user_id)
    if blocked:
        return {
            "query": query,
            "answer": blocked,
            "reference": [],
        }

    retrieval_strategy, document_ids = resolve_session_retrieval(session_id, user_id=user_id)
    request_doc_ids = normalize_id_list(extra_doc_ids)
    if request_doc_ids and retrieval_strategy == "load_in_context":
        before = len(document_ids)
        document_ids = merge_unique_ids(document_ids, request_doc_ids)
        logger.info(
            "admin_retrieve_and_answer: merged request doc_ids extra={} "
            "document_ids {} -> {}",
            len(request_doc_ids),
            before,
            len(document_ids),
        )
    logger.info(
        "admin_retrieve_and_answer: session_id={} strategy={} document_ids={}",
        normalize_session_id(session_id),
        retrieval_strategy,
        len(document_ids),
    )

    searcher = LexChunkSearch()
    candidates = searcher.search(
        query,
        candidate_size=candidate_size,
        similarity_threshold=similarity_threshold,
        keyword_weight=keyword_weight,
        field_weights=field_weights,
        topic_ids=topic_ids,
        subject_ids=subject_ids,
    )
    logger.info(
        "admin_retrieve_and_answer: es_candidates={} threshold={} final_size={}",
        len(candidates),
        similarity_threshold,
        final_size,
    )

    reranked = rerank_hits(
        query,
        candidates,
        final_size=final_size,
        reranker=reranker,
    )

    user_doc_hits: list[dict[str, Any]] = []
    if retrieval_strategy == "load_in_context" and document_ids:
        user_doc_hits = searcher.retrieval_document(query, document_ids)
        logger.info(
            "admin_retrieve_and_answer: load_in_context user_chunks={}",
            len(user_doc_hits),
        )

    legal_context = chunks_to_context(reranked)
    user_upload_context = ""
    if user_doc_hits:
        start = len(reranked) + 1 if reranked else 1
        user_upload_context = chunks_to_context(user_doc_hits, start_index=start)

    hits_for_references = list(reranked) + list(user_doc_hits)
    end_conversation, legal_context = should_end_conversation(
        legal_context,
        user_upload_context,
    )

    sid = normalize_session_id(session_id)
    if end_conversation and sid:
        ChatSessionService.mark_use_up_token(session_id=sid, user_id=user_id)

    answer, cited_indexes = generate_answer_with_citations(
        query,
        legal_context,
        user_upload_context=user_upload_context or None,
    )
    references = build_references(hits_for_references, cited_indexes)

    logger.info(
        "admin_retrieve_and_answer: cited_indexes={} references={}",
        cited_indexes,
        len(references),
    )

    return {
        "query": query,
        "answer": answer,
        "reference": references,
    }


def _chunk_hit_key(hit: dict[str, Any]) -> str:
    for key in ("chunk_id", "_id", "id"):
        value = hit.get(key)
        if value:
            return str(value)
    return str(id(hit))


def admin_retrieve_and_answer_multi(
    *,
    queries: list[str],
    primary_query: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    candidate_size: int = 100,
    similarity_threshold: float = 0.5,
    final_size: int = 5,
    keyword_weight: float = 0.3,
    field_weights: list[str] | None = None,
    topic_ids: list[str] | None = None,
    subject_ids: list[str] | None = None,
    extra_doc_ids: list[str] | None = None,
    reranker: BgeM3Reranker | None = None,
) -> dict[str, Any]:
    """Hybrid search với nhiều câu truy vấn, gộp hit rồi rerank + trả lời một lần."""
    normalized = []
    for q in queries or []:
        text = str(q or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    primary = (primary_query or (normalized[0] if normalized else "")).strip()
    if not normalized:
        return admin_retrieve_and_answer(
            query=primary,
            session_id=session_id,
            user_id=user_id,
            candidate_size=candidate_size,
            similarity_threshold=similarity_threshold,
            final_size=final_size,
            keyword_weight=keyword_weight,
            field_weights=field_weights,
            topic_ids=topic_ids,
            subject_ids=subject_ids,
            extra_doc_ids=extra_doc_ids,
            reranker=reranker,
        )
    if len(normalized) == 1:
        return admin_retrieve_and_answer(
            query=normalized[0],
            session_id=session_id,
            user_id=user_id,
            candidate_size=candidate_size,
            similarity_threshold=similarity_threshold,
            final_size=final_size,
            keyword_weight=keyword_weight,
            field_weights=field_weights,
            topic_ids=topic_ids,
            subject_ids=subject_ids,
            extra_doc_ids=extra_doc_ids,
            reranker=reranker,
        )

    blocked = session_blocked_message(session_id, user_id=user_id)
    if blocked:
        return {"query": primary, "answer": blocked, "reference": []}

    retrieval_strategy, document_ids = resolve_session_retrieval(session_id, user_id=user_id)
    request_doc_ids = normalize_id_list(extra_doc_ids)
    if request_doc_ids and retrieval_strategy == "load_in_context":
        document_ids = merge_unique_ids(document_ids, request_doc_ids)

    searcher = LexChunkSearch()
    merged_candidates: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    per_query_cap = max(20, candidate_size // max(1, len(normalized)))

    for q in normalized:
        hits = searcher.search(
            q,
            candidate_size=per_query_cap,
            similarity_threshold=similarity_threshold,
            keyword_weight=keyword_weight,
            field_weights=field_weights,
            topic_ids=topic_ids,
            subject_ids=subject_ids,
        )
        for hit in hits:
            key = _chunk_hit_key(hit)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            merged_candidates.append(hit)

    logger.info(
        "admin_retrieve_and_answer_multi: queries={} merged_candidates={}",
        len(normalized),
        len(merged_candidates),
    )

    reranked = rerank_hits(
        primary,
        merged_candidates,
        final_size=final_size,
        reranker=reranker,
    )

    user_doc_hits: list[dict[str, Any]] = []
    if retrieval_strategy == "load_in_context" and document_ids:
        user_doc_hits = searcher.retrieval_document(primary, document_ids)

    legal_context = chunks_to_context(reranked)
    user_upload_context = ""
    if user_doc_hits:
        start = len(reranked) + 1 if reranked else 1
        user_upload_context = chunks_to_context(user_doc_hits, start_index=start)

    hits_for_references = list(reranked) + list(user_doc_hits)
    end_conversation, legal_context = should_end_conversation(
        legal_context,
        user_upload_context,
    )

    sid = normalize_session_id(session_id)
    if end_conversation and sid:
        ChatSessionService.mark_use_up_token(session_id=sid, user_id=user_id)

    answer, cited_indexes = generate_answer_with_citations(
        primary,
        legal_context,
        user_upload_context=user_upload_context or None,
    )
    references = build_references(hits_for_references, cited_indexes)

    return {
        "query": primary,
        "answer": answer,
        "reference": references,
        "search_queries": normalized,
    }
