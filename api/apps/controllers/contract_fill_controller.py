from __future__ import annotations

from typing import Any

from fastapi.responses import StreamingResponse

from api.apps.controllers.chat_controller import _load_chat_history, _normalize_session_id, _normalize_user_id
from api.apps.services.contract_draft_session import sync_contract_draft_from_envelope
from api.apps.services.contract_fill_service import run_contract_fill, stream_contract_fill
from api.db.models import Users
from api.utils.logger import setup_logging

logger = setup_logging()


def contract_fill(
    *,
    user: Users,
    query: str,
    template_document_id: str | None = None,
    session_id: str | None = None,
    thread_id: str | None = None,
    resume: dict | None = None,
) -> dict[str, Any]:
    try:
        raw_query = (query or "").strip()
        if not raw_query:
            return {"code": 400, "msg": "query is required", "data": None}

        persist_session_id = _normalize_session_id(session_id)
        user_id = _normalize_user_id(user.id)
        chat_history = _load_chat_history(
            session_id=persist_session_id, user_id=user_id
        )

        tid = (template_document_id or "").strip() or None
        payload = run_contract_fill(
            user=user,
            query=raw_query,
            template_document_id=tid,
            session_id=persist_session_id,
            chat_history=chat_history,
            thread_id=thread_id,
            resume=resume,
        )
        if persist_session_id and payload.get("ui_template") == "task_execution":
            sync_contract_draft_from_envelope(
                session_id=persist_session_id,
                user_id=user_id,
                envelope=payload,
            )
        return {"code": 200, "msg": "OK", "data": payload}
    except PermissionError as e:
        return {"code": 403, "msg": str(e), "data": None}
    except LookupError as e:
        return {"code": 404, "msg": str(e), "data": None}
    except ValueError as e:
        return {"code": 400, "msg": str(e), "data": None}
    except Exception as e:
        logger.error("contract_fill error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}


def contract_fill_stream(
    *,
    user: Users,
    query: str,
    template_document_id: str | None = None,
    session_id: str | None = None,
    thread_id: str | None = None,
    resume: dict | None = None,
) -> StreamingResponse | dict[str, Any]:
    try:
        raw_query = (query or "").strip()
        if not raw_query:
            return {"code": 400, "msg": "query is required", "data": None}
        persist_session_id = _normalize_session_id(session_id)
        user_id = _normalize_user_id(user.id)
        chat_history = _load_chat_history(
            session_id=persist_session_id, user_id=user_id
        )
        tid = (template_document_id or "").strip() or None

        async def event_gen():
            async for chunk in stream_contract_fill(
                user=user,
                query=raw_query,
                template_document_id=tid,
                session_id=persist_session_id,
                chat_history=chat_history,
                thread_id=thread_id,
                resume=resume,
            ):
                yield chunk

        return StreamingResponse(
            event_gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except PermissionError as e:
        return {"code": 403, "msg": str(e), "data": None}
    except LookupError as e:
        return {"code": 404, "msg": str(e), "data": None}
    except ValueError as e:
        return {"code": 400, "msg": str(e), "data": None}
    except Exception as e:
        logger.error("contract_fill_stream error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}
