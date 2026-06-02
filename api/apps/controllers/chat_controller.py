from __future__ import annotations

from fastapi import UploadFile

from api.apps.services.chat_service import ChatMessageService, ChatSessionService
from api.apps.services.user_document_service import process_user_file_upload
from api.db.models import ChatMessage, ChatSession, Users
from api.utils.logger import setup_logging

logger = setup_logging()


def _normalize_session_id(session_id: str | None) -> str | None:
    if session_id is None:
        return None
    s = str(session_id).strip()
    if s.lower() in ("", "null", "undefined", "none"):
        return None
    return s


def _normalize_user_id(user_id: str | None) -> str | None:
    if user_id is None:
        return None
    s = str(user_id).strip()
    return s or None


def _session_to_dict(row: ChatSession) -> dict:
    return {
        "id": row.id,
        "user_id": _normalize_user_id(row.user_id),
        "title": row.title,
        "status": row.status,
        "metadata": row.metadata or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _message_to_dict(row: ChatMessage) -> dict:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "user_id": _normalize_user_id(row.user_id),
        "role": row.role,
        "content": row.content,
        "references": row.message_references or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def delete_user_chat_session(*, user: Users, session_id: str | None) -> dict:
    try:
        sid = _normalize_session_id(session_id)
        uid = _normalize_user_id(user.id)
        if not sid:
            return {"code": 400, "msg": "session_id is required", "data": None}
        if not uid:
            return {"code": 401, "msg": "Invalid user id", "data": None}

        logger.info("delete_user_chat_session: user_id={} session_id={}", uid, sid)
        ok = ChatSessionService.mark_deleted(session_id=sid, user_id=uid)
        if ok is None:
            return {"code": 404, "msg": "Session not found", "data": None}
        if ok is False:
            return {"code": 403, "msg": "Session does not belong to this user", "data": None}

        logger.info("delete_user_chat_session: marked deleted session_id={}", sid)
        return {"code": 200, "msg": "OK", "data": {"session_id": sid, "status": "deleted"}}
    except Exception as e:
        logger.error("delete_user_chat_session error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}


def list_user_chat_sessions(
    *,
    user: Users,
    page: int = 1,
    page_size: int = 5,
) -> dict:
    try:
        uid = _normalize_user_id(user.id)
        if not uid:
            return {"code": 401, "msg": "Invalid user id", "data": None}
        logger.info(
            "list_user_chat_sessions: user_id={} page={} page_size={}",
            uid,
            page,
            page_size,
        )
        total, rows = ChatSessionService.list_active_by_user_paginated(
            uid, page, page_size
        )
        logger.info(
            "list_user_chat_sessions: user_id={} total={} returned={}",
            uid,
            total,
            len(rows),
        )
        return {
            "code": 200,
            "msg": "OK",
            "data": {
                "total": total,
                "page": max(1, page),
                "page_size": max(1, min(page_size, 100)),
                "items": [_session_to_dict(r) for r in rows],
            },
        }
    except Exception as e:
        logger.error("list_user_chat_sessions error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}


def get_user_chat_session_messages(*, user: Users, session_id: str | None) -> dict:
    try:
        sid = _normalize_session_id(session_id)
        uid = _normalize_user_id(user.id)
        if not sid:
            return {"code": 400, "msg": "session_id is required", "data": None}
        if not uid:
            return {"code": 401, "msg": "Invalid user id", "data": None}

        logger.info(
            "get_user_chat_session_messages: user_id={} session_id={}",
            uid,
            sid,
        )
        session = ChatSessionService.get_session(sid)
        if not session:
            return {"code": 404, "msg": "Session not found", "data": None}
        if _normalize_user_id(session.user_id) != uid:
            return {"code": 403, "msg": "Session does not belong to this user", "data": None}
        if session.status == "deleted":
            return {"code": 404, "msg": "Session not found", "data": None}

        messages = ChatMessageService.list_by_session_and_user(
            session_id=sid,
            user_id=uid,
        )
        logger.info(
            "get_user_chat_session_messages: session_id={} message_count={}",
            sid,
            len(messages),
        )
        return {
            "code": 200,
            "msg": "OK",
            "data": {
                "session": _session_to_dict(session),
                "messages": [_message_to_dict(m) for m in messages],
            },
        }
    except Exception as e:
        logger.error("get_user_chat_session_messages error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}


async def upload_user_file(
    *,
    user: Users,
    file: UploadFile,
    session_id: str | None = None,
) -> dict:
    try:
        logger.info(
            "upload_user_file: user_id={} filename={} session_id={}",
            user.id,
            file.filename,
            session_id,
        )
        return await process_user_file_upload(
            user=user,
            file=file,
            session_id=session_id,
        )
    except Exception as e:
        logger.error("upload_user_file error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}
