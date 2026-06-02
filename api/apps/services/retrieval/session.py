from __future__ import annotations

from typing import Any

from api.apps.services.chat_service import ChatSessionService
from api.utils.logger import setup_logging

from .constants import BLOCKED_SESSION_STATUSES, SESSION_TOKEN_EXHAUSTED_MSG

logger = setup_logging()


def normalize_session_id(session_id: str | None) -> str | None:
    if session_id is None:
        return None
    s = str(session_id).strip()
    if s.lower() in ("", "null", "undefined", "none"):
        return None
    return s


def normalize_id_list(ids: list[str] | None) -> list[str]:
    if not ids:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for raw in ids:
        s = str(raw).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def merge_unique_ids(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for raw in group:
            s = str(raw).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
    return out


def document_ids_from_session_metadata(metadata: dict[str, Any] | None) -> list[str]:
    meta = metadata or {}
    doc_ids = [str(d).strip() for d in (meta.get("document_ids") or []) if str(d).strip()]
    if doc_ids:
        return list(dict.fromkeys(doc_ids))
    seen: set[str] = set()
    out: list[str] = []
    for item in meta.get("uploads") or []:
        if not isinstance(item, dict):
            continue
        did = str(item.get("document_id") or "").strip()
        if did and did not in seen:
            seen.add(did)
            out.append(did)
    return out


def resolve_session_retrieval(
    session_id: str | None,
    *,
    user_id: str | None = None,
) -> tuple[str | None, list[str]]:
    """Trả về (retrieval_strategy, document_ids) từ chat_sessions.metadata."""
    sid = normalize_session_id(session_id)
    if not sid:
        return None, []

    session = ChatSessionService.get_session(sid)
    if not session:
        logger.warning("admin_retrieve_and_answer: session not found id={}", sid)
        return None, []
    if user_id and session.user_id != user_id:
        raise PermissionError("Session does not belong to this user")
    if (session.status or "").strip() in BLOCKED_SESSION_STATUSES:
        return None, []

    meta = session.metadata if isinstance(session.metadata, dict) else {}
    strategy = str(meta.get("retrieval_strategy") or "").strip() or None
    doc_ids = document_ids_from_session_metadata(meta)
    return strategy, doc_ids


def session_blocked_message(
    session_id: str | None,
    *,
    user_id: str | None = None,
) -> str | None:
    """Trả về thông báo lỗi nếu session deleted / use_up_token; None nếu được phép chat."""
    sid = normalize_session_id(session_id)
    if not sid:
        return None

    session = ChatSessionService.get_session(sid)
    if not session:
        return None
    if user_id and session.user_id != user_id:
        raise PermissionError("Session does not belong to this user")
    if (session.status or "").strip() in BLOCKED_SESSION_STATUSES:
        return SESSION_TOKEN_EXHAUSTED_MSG
    return None
