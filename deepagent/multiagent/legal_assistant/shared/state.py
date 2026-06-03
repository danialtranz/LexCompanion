from __future__ import annotations

from typing import Any, Literal, TypedDict

IntentType = Literal[
    "information",
    "decision",
    "task_execution",
    "problem_solving",
    "exploration",
    "communication_normal",
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
    resolved_user_request: str
    intent_resolution_reason: str
    rag_search_queries: list[str]
    rag_matched_topic_ids: list[str]
    rag_requery_reason: str
    rag_iteration: int
    retrieval_attempts: list[dict[str, Any]]
    is_context_sufficient: bool
    insufficiency_reason: str
    query_expansion_hint: str
    needs_user_clarification: bool
    missing_facts: list[str]
    clarification_questions: list[str]
    partial_answer_preface: str
    hitl_assessment_reason: str
    hitl_used: bool
    reason_phase: Literal["rag", "web"]
    web_search_used: bool
    web_results: list[dict[str, Any]]

    # Per-intent enrichments
    decision_options: list[str]
    task_checklist: list[str]
    problem_plan: list[str]
    exploration_options: list[dict[str, Any]]

    # Contract form fill (task_execution)
    template_document_id: str | None
    template_suffix: str | None
    template_markdown: str | None
    layout_items: list[dict[str, Any]]
    form_schema: list[dict[str, Any]]
    filled_values: dict[str, str]
    draft_version: int
    draft_object_key: str | None
    draft_output_suffix: str | None
    form_hitl: dict[str, Any]
    answer_mode: str | None
    contract_kb_id: str | None
    contract_tenant_id: str | None
    contract_file_location: str | None
    session_uploads: list[dict[str, Any]]
    thread_id: str | None

    # Standard output
    response: str | None
    output: dict[str, Any]
