from __future__ import annotations

from typing import Any

from api.utils.logger import setup_logging
from deepagent.multiagent.legal_assistant.registry import run_graph
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState

from .intent_router import route_intent
from .schemas import ChatOrchestratorInput

logger = setup_logging()


def run_chat_orchestrator(payload: ChatOrchestratorInput) -> dict[str, Any]:
    decision = route_intent(
        query=payload.query,
        session_id=payload.session_id,
        user_id=payload.user_id,
    )
    logger.info(
        "chat_orchestrator: intent={} confidence={} query_len={}",
        decision.intent,
        decision.confidence,
        len(payload.query or ""),
    )
    state: LegalAssistantState = {
        "user_query": payload.query,
        "intent": decision.intent,
        "confidence": decision.confidence,
        "session_id": payload.session_id,
        "user_id": payload.user_id,
        "candidate_size": payload.candidate_size,
        "similarity_threshold": payload.similarity_threshold,
        "final_size": payload.final_size,
        "keyword_weight": payload.keyword_weight,
        "field_weights": payload.field_weights,
        "topic_ids": payload.topic_ids,
        "subject_ids": payload.subject_ids,
        "doc_ids": payload.doc_ids,
        "reranker": payload.reranker,
    }
    result = run_graph(decision.intent, state)
    output = result.get("output")
    if isinstance(output, dict):
        return output
    return {
        "query": payload.query,
        "answer": result.get("response"),
        "reference": result.get("citations") or [],
    }
