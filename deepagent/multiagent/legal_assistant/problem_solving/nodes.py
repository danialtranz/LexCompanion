from __future__ import annotations

from deepagent.multiagent.legal_assistant.problem_solving.strategy import (
    build_problem_strategy,
)
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.tools.legal_retrieval import run_legal_retrieval


def run_problem_solving_flow(state: LegalAssistantState) -> LegalAssistantState:
    query = state.get("user_query", "")
    retrieval_payload = run_legal_retrieval(
        query=query,
        session_id=state.get("session_id"),
        user_id=state.get("user_id"),
        candidate_size=state.get("candidate_size", 100),
        similarity_threshold=state.get("similarity_threshold", 0.5),
        final_size=state.get("final_size", 5),
        keyword_weight=state.get("keyword_weight", 0.3),
        field_weights=state.get("field_weights"),
        topic_ids=state.get("topic_ids"),
        subject_ids=state.get("subject_ids"),
        doc_ids=state.get("doc_ids"),
        reranker=state.get("reranker"),
    )
    plan = build_problem_strategy()

    next_state = dict(state)
    next_state["problem_plan"] = plan
    next_state["output"] = {
        **retrieval_payload,
        "problem_plan": plan,
    }
    next_state["response"] = next_state["output"].get("answer")
    return next_state
