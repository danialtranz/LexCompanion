from __future__ import annotations

from typing import Any, Literal, TypedDict

IntentType = Literal[
    "information",
    "decision",
    "task_execution",
    "problem_solving",
    "exploration",
]


class LegalAssistantState(TypedDict, total=False):
    user_query: str
    intent: IntentType
    confidence: float
    session_id: str | None
    user_id: str | None
    candidate_size: int
    similarity_threshold: float
    final_size: int
    keyword_weight: float
    field_weights: list[str] | None
    topic_ids: list[str] | None
    subject_ids: list[str] | None
    doc_ids: list[str] | None
    reranker: Any | None
    chat_history: list[dict[str, Any]]

    # Retrieval / references
    retrieval_payload: dict[str, Any]
    citations: list[dict[str, Any]]
    rewritten_query: str
    rag_iteration: int
    retrieval_attempts: list[dict[str, Any]]
    is_context_sufficient: bool
    insufficiency_reason: str
    query_expansion_hint: str
    web_search_used: bool
    web_results: list[dict[str, Any]]

    # Per-intent enrichments
    decision_options: list[str]
    task_checklist: list[str]
    problem_plan: list[str]
    exploration_options: list[dict[str, Any]]

    # Standard output
    response: str | None
    output: dict[str, Any]
