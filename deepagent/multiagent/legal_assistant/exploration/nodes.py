from __future__ import annotations

from deepagent.multiagent.legal_assistant.exploration.scorers import score_options
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.tools.legal_retrieval import run_legal_retrieval
from deepagent.multiagent.legal_assistant.tools.web_search import run_web_search


def run_exploration_flow(state: LegalAssistantState) -> LegalAssistantState:
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
    web = run_web_search(query=query, limit=3)
    options = score_options(
        [
            {
                "name": "Phuong an an toan",
                "tradeoff": "Toc do trung binh, rui ro thap",
            },
            {
                "name": "Phuong an nhanh",
                "tradeoff": "Toc do cao, can bo sung tai lieu",
            },
        ]
    )

    next_state = dict(state)
    next_state["exploration_options"] = options
    next_state["output"] = {
        **retrieval_payload,
        "exploration_options": options,
        "web_search": web,
    }
    next_state["response"] = next_state["output"].get("answer")
    return next_state
