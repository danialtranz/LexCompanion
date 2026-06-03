from __future__ import annotations

import json
from typing import Any, AsyncIterator

from api.apps.services.chat_service import ChatSessionService
from api.db.models import DB, Users
from deepagent.multiagent.legal_assistant.task_execution.session_documents import (
    resolve_doc_ids_from_state,
)
from api.utils.logger import setup_logging
from deepagent.core.hitl.checkpoint import default_thread_id
from deepagent.multiagent.legal_assistant.registry import invoke_task_execution_graph
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState

logger = setup_logging()

CONTRACT_META_KEY = "contract_fill"


def _sse_line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_contract_fill_state(
    *,
    user: Users,
    query: str,
    template_document_id: str | None,
    session_id: str | None,
    chat_history: list[dict[str, Any]] | None = None,
    doc_ids: list[str] | None = None,
) -> LegalAssistantState:
    ids = [d for d in (doc_ids or []) if d]
    if template_document_id and template_document_id not in ids:
        ids = [template_document_id, *ids]
    session_uploads: list[dict[str, Any]] = []
    resolved_ids = ids
    if session_id:
        resolved_ids, session_uploads = resolve_doc_ids_from_state(
            doc_ids=ids or None,
            session_id=session_id,
            user_id=user.id,
        )
    return {
        "user_query": query,
        "resolved_user_request": query,
        "chat_history": chat_history or [],
        "intent": "task_execution",
        "session_id": session_id,
        "user_id": user.id,
        "doc_ids": resolved_ids or None,
        "session_uploads": session_uploads,
        "template_document_id": template_document_id,
    }


@DB.connection_context()
def run_contract_fill(
    *,
    user: Users,
    query: str,
    template_document_id: str | None = None,
    session_id: str | None = None,
    chat_history: list[dict[str, Any]] | None = None,
    thread_id: str | None = None,
    resume: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = build_contract_fill_state(
        user=user,
        query=query,
        template_document_id=template_document_id,
        session_id=session_id,
        chat_history=chat_history,
        doc_ids=[template_document_id] if template_document_id else None,
    )
    tid = thread_id or default_thread_id(
        session_id=session_id,
        user_id=user.id,
        intent="task_execution",
    )
    envelope = invoke_task_execution_graph(
        state, thread_id=tid, resume=resume, query_fallback=query
    )
    if session_id and envelope.get("status") == "completed":
        answer = envelope.get("answer") or envelope.get("message")
        if answer:
            ChatSessionService.save_retrieval_exchange(
                session_id=session_id,
                user=user,
                query=query,
                answer=str(answer),
                references=[],
            )
    return envelope


async def stream_contract_fill(
    *,
    user: Users,
    query: str,
    template_document_id: str | None = None,
    session_id: str | None = None,
    chat_history: list[dict[str, Any]] | None = None,
    thread_id: str | None = None,
    resume: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    yield _sse_line({"type": "status", "message": "Đang chạy task_execution..."})
    try:
        envelope = run_contract_fill(
            user=user,
            query=query,
            template_document_id=template_document_id,
            session_id=session_id,
            chat_history=chat_history,
            thread_id=thread_id,
            resume=resume,
        )
    except Exception as e:
        yield _sse_line({"type": "error", "message": str(e)})
        return

    if envelope.get("status") == "waiting_human":
        msg = envelope.get("message") or ""
        for i in range(0, len(msg), 24):
            yield _sse_line({"type": "token", "delta": msg[i : i + 24]})
    yield _sse_line({"type": "done", "data": envelope})
