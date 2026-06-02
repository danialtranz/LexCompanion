from __future__ import annotations

from deepagent.multiagent.legal_assistant.decision.calculators import compute_decision_estimate
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.tools.legal_retrieval import run_legal_retrieval


def run_decision_flow(state: LegalAssistantState) -> LegalAssistantState:
    retrieval_payload = run_legal_retrieval(
        query=state.get("user_query", ""),
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
    estimate = compute_decision_estimate(state.get("user_query", ""))
    next_state = dict(state)
    next_state["retrieval_payload"] = retrieval_payload
    next_state["decision_options"] = [
        "Thu thập thêm dữ kiện còn thiếu trước khi ra quyết định cuối.",
        "Ưu tiên hành động giảm rủi ro pháp lý ngay lập tức.",
    ]
    next_state["output"] = {
        **retrieval_payload,
        "decision_estimate": estimate,
        "decision_options": next_state["decision_options"],
    }
    next_state["response"] = next_state["output"].get("answer")
    return next_state
