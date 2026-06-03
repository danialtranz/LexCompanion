from __future__ import annotations

from typing import Any

from api.apps.services.retrieval import (
    admin_retrieve_and_answer,
    admin_retrieve_and_answer_multi,
)


def run_legal_retrieval(
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
    doc_ids: list[str] | None = None,
    reranker: Any | None = None,
) -> dict[str, Any]:
    return admin_retrieve_and_answer(
        query=query,
        session_id=session_id,
        user_id=user_id,
        candidate_size=candidate_size,
        similarity_threshold=similarity_threshold,
        final_size=final_size,
        keyword_weight=keyword_weight,
        field_weights=field_weights,
        topic_ids=topic_ids,
        subject_ids=subject_ids,
        extra_doc_ids=doc_ids,
        reranker=reranker,
    )


def run_legal_retrieval_multi(
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
    doc_ids: list[str] | None = None,
    reranker: Any | None = None,
) -> dict[str, Any]:
    return admin_retrieve_and_answer_multi(
        queries=queries,
        primary_query=primary_query,
        session_id=session_id,
        user_id=user_id,
        candidate_size=candidate_size,
        similarity_threshold=similarity_threshold,
        final_size=final_size,
        keyword_weight=keyword_weight,
        field_weights=field_weights,
        topic_ids=topic_ids,
        subject_ids=subject_ids,
        extra_doc_ids=doc_ids,
        reranker=reranker,
    )
