from __future__ import annotations

from typing import Any

from api.apps.services.chat_service import ChatSessionService
from api.db.models import DB
from api.utils.logger import setup_logging
from deepagent.core.hitl.checkpoint import default_thread_id
from deepagent.multiagent.legal_assistant.registry import (
    invoke_task_execution_graph,
    run_graph,
)
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.task_execution.session_documents import (
    resolve_doc_ids_from_state,
)

from .intent_router import route_intent
from .schemas import ChatOrchestratorInput, RoutingDecision

logger = setup_logging()


@DB.connection_context()
def _persist_hitl_checkpoint_meta(
    *,
    session_id: str,
    user_id: str,
    envelope: dict[str, Any],
) -> None:
    session = ChatSessionService.get_session(session_id)
    if not session or str(session.user_id) != str(user_id):
        return
    meta = dict(session.metadata or {})
    if envelope.get("status") == "waiting_human":
        meta["hitl_checkpoint"] = {
            "thread_id": envelope.get("thread_id"),
            "status": "waiting_human",
            "kind": (envelope.get("hitl") or {}).get("kind"),
        }
    elif envelope.get("status") == "completed":
        meta.pop("hitl_checkpoint", None)
    session.metadata = meta
    session.save()


def _resolve_routing_decision(payload: ChatOrchestratorInput) -> RoutingDecision:
    if (payload.ui_template or "").strip() == "task_execution":
        return RoutingDecision(
            intent="task_execution",
            confidence=1.0,
            reason="client_ui_template",
        )
    return route_intent(
        query=payload.query,
        session_id=payload.session_id,
        user_id=payload.user_id,
    )


@DB.connection_context()
def run_chat_orchestrator(payload: ChatOrchestratorInput) -> dict[str, Any]:
    decision = _resolve_routing_decision(payload)
    logger.info(
        "chat_orchestrator: intent={} confidence={} ui_template={} query_len={}",
        decision.intent,
        decision.confidence,
        payload.ui_template,
        len(payload.query or ""),
    )

    thread_id = payload.thread_id or default_thread_id(
        session_id=payload.session_id,
        user_id=payload.user_id,
        intent=decision.intent,
    )

    state: LegalAssistantState = {
        "user_query": payload.query,
        "resolved_user_request": payload.query,
        "chat_history": payload.chat_history or [],
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
        "thread_id": thread_id,
    }

    if decision.intent == "task_execution":
        doc_ids_resolved, session_uploads = resolve_doc_ids_from_state(
            doc_ids=state.get("doc_ids"),
            session_id=payload.session_id,
            user_id=payload.user_id,
        )
        state["doc_ids"] = doc_ids_resolved or None
        state["session_uploads"] = session_uploads

        envelope = invoke_task_execution_graph(
            state,
            thread_id=thread_id,
            resume=payload.resume,
            query_fallback=payload.query,
        )
        envelope["ui_template"] = "task_execution"
        if payload.session_id and payload.user_id:
            _persist_hitl_checkpoint_meta(
                session_id=payload.session_id,
                user_id=payload.user_id,
                envelope=envelope,
            )
        return envelope

    result = run_graph(decision.intent, state)
    output = result.get("output")
    if isinstance(output, dict):
        return {
            "status": "completed",
            "message": output.get("answer") or result.get("response"),
            "thread_id": thread_id,
            "hitl": None,
            "resume": None,
            **output,
        }
    return {
        "status": "completed",
        "message": result.get("response"),
        "thread_id": thread_id,
        "hitl": None,
        "resume": None,
        "query": payload.query,
        "answer": result.get("response"),
        "reference": result.get("citations") or [],
    }
