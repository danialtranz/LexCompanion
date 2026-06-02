from __future__ import annotations

from typing import Any

from api.apps.services.common_service import CommonService
from api.db.models import ChatMessage, ChatSession, DB, Users
from api.utils.logger import setup_logging
from api.utils.utils import get_uuid

logger = setup_logging()

_SESSION_TITLE_MAX_LEN = 200


def _normalize_user_id(user_id: str | None) -> str | None:
    if user_id is None:
        return None
    s = str(user_id).strip()
    return s or None


class ChatSessionService(CommonService):
    model = ChatSession
    @classmethod
    @DB.connection_context()
    def get_session(cls, session_id: str) -> ChatSession | None:
        return ChatSession.get_or_none(ChatSession.id == session_id)

    @classmethod
    def _ensure_session_in_tx(
        cls,
        *,
        session_id: str,
        user: Users,
        title_hint: str | None = None,
    ) -> ChatSession:
        normalized_user_id = _normalize_user_id(user.id)
        if not normalized_user_id:
            raise ValueError("Invalid user id")

        session = ChatSession.get_or_none(ChatSession.id == session_id)
        if session:
            if _normalize_user_id(session.user_id) != normalized_user_id:
                raise PermissionError("Session does not belong to this user")
            if title_hint and not (session.title or "").strip():
                session.title = title_hint.strip()[:_SESSION_TITLE_MAX_LEN] or None
            session.save()
            return session

        title = (title_hint or "").strip()[:_SESSION_TITLE_MAX_LEN] or None
        session = ChatSession.create(
            id=session_id,
            user_id=normalized_user_id,
            title=title,
            status="active",
            metadata={},
        )
        logger.info(
            "chat_session created id={} user_id={}",
            session_id,
            normalized_user_id,
        )
        return session

    @classmethod
    @DB.connection_context()
    def ensure_session(
        cls,
        *,
        session_id: str,
        user: Users,
        title_hint: str | None = None,
    ) -> ChatSession:
        return cls._ensure_session_in_tx(
            session_id=session_id,
            user=user,
            title_hint=title_hint,
        )

    @classmethod
    @DB.connection_context()
    def save_retrieval_exchange(
        cls,
        *,
        session_id: str,
        user: Users,
        query: str,
        answer: str,
        references: list[Any] | None = None,
    ) -> None:
        normalized_user_id = _normalize_user_id(user.id)
        if not normalized_user_id:
            raise ValueError("Invalid user id")

        cls._ensure_session_in_tx(
            session_id=session_id,
            user=user,
            title_hint=query,
        )
        refs = references if references else []

        ChatMessage.create(
            id=get_uuid(),
            session_id=session_id,
            user_id=normalized_user_id,
            role="user",
            content=query,
            message_references=[],
        )
        ChatMessage.create(
            id=get_uuid(),
            session_id=session_id,
            user_id=normalized_user_id,
            role="assistant",
            content=answer,
            message_references=refs,
        )
        logger.info(
            "chat_messages saved session_id={} refs={}",
            session_id,
            len(refs),
        )

    @classmethod
    @DB.connection_context()
    def mark_use_up_token(cls, *, session_id: str, user_id: str | None = None) -> bool:
        """Đánh dấu session đã vượt ngân sách context (status=use_up_token)."""
        session = cls.get_or_none(id=session_id)
        if not session:
            return False
        normalized_user_id = _normalize_user_id(user_id)
        if normalized_user_id and _normalize_user_id(session.user_id) != normalized_user_id:
            return False
        session.status = "use_up_token"
        session.save()
        logger.info("chat_session use_up_token id={}", session_id)
        return True

    @classmethod
    @DB.connection_context()
    def mark_deleted(cls, *, session_id: str, user_id: str) -> bool | None:
        """Đánh dấu session deleted. None=không tồn tại, False=không thuộc user, True=OK."""
        normalized_user_id = _normalize_user_id(user_id)
        if not normalized_user_id:
            return False
        session = cls.get_or_none(id=session_id)
        if not session:
            return None
        if _normalize_user_id(session.user_id) != normalized_user_id:
            return False
        session.status = "deleted"
        session.save()
        return True

    @classmethod
    @DB.connection_context()
    def list_active_by_user_paginated(
        cls, user_id: str, page: int, page_size: int
    ) -> tuple[int, list[ChatSession]]:
        """Sessions của user có status khác 'deleted', sắp xếp updated_at giảm dần."""
        normalized_user_id = _normalize_user_id(user_id)
        if not normalized_user_id:
            return 0, []
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        q = (
            cls.model.select()
            .where(
                (cls.model.user_id == normalized_user_id)
                & (
                    (cls.model.status != "deleted") | (cls.model.status.is_null())
                )
            )
            .order_by(cls.model.updated_at.desc())
        )
        total = q.count()
        rows = list(q.paginate(page, page_size))
        return total, rows


class ChatMessageService(CommonService):
    model = ChatMessage

    @classmethod
    @DB.connection_context()
    def list_by_session_and_user(
        cls, *, session_id: str, user_id: str
    ) -> list[ChatMessage]:
        """Tin nhắn trong session của user, sắp xếp theo created_at tăng dần."""
        normalized_user_id = _normalize_user_id(user_id)
        if not normalized_user_id:
            return []
        return list(
            cls.model.select()
            .where(
                (cls.model.session_id == session_id)
                & (cls.model.user_id == normalized_user_id)
            )
            .order_by(cls.model.created_at.asc())
        )
