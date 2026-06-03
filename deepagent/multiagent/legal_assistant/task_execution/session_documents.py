from __future__ import annotations

from typing import Any

from api.apps.services.chat_service import ChatSessionService


def load_session_uploads(
    *,
    session_id: str | None,
    user_id: str | None,
) -> list[dict[str, Any]]:
    """Đọc metadata.uploads từ chat_sessions."""
    if not session_id or not user_id:
        return []
    session = ChatSessionService.get_session(session_id)
    if not session:
        return []
    if str(session.user_id) != str(user_id):
        return []
    meta = dict(session.metadata or {})
    uploads = meta.get("uploads") or []
    if not isinstance(uploads, list):
        return []
    return [u for u in uploads if isinstance(u, dict) and u.get("document_id")]


def resolve_doc_ids_from_state(
    *,
    doc_ids: list[str] | None,
    session_uploads: list[dict[str, Any]] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Ưu tiên doc_ids từ state; nếu rỗng thì lấy từ session_uploads (đã preload) hoặc DB.
    """
    explicit = [str(d).strip() for d in (doc_ids or []) if str(d).strip()]
    if session_uploads is not None:
        uploads = list(session_uploads)
    elif session_id and user_id:
        uploads = load_session_uploads(session_id=session_id, user_id=user_id)
    else:
        uploads = []
    if explicit:
        return explicit, uploads
    from_session = [
        str(u["document_id"]).strip()
        for u in uploads
        if u.get("document_id")
    ]
    return from_session, uploads
