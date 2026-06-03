from __future__ import annotations

import mimetypes
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import Response

from api.apps.services.chat_service import ChatSessionService
from api.apps.services.contract_fill_service import CONTRACT_META_KEY
from api.db.models import Users
from api.utils.minio_conn import LexCompanionMinio


def stream_contract_draft(*, user: Users, session_id: str) -> Response:
    session = ChatSessionService.get_session(session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    meta = dict(session.metadata or {})
    contract = meta.get(CONTRACT_META_KEY) or {}
    if not isinstance(contract, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No contract draft")
    draft_key = (contract.get("draft_object_key") or "").strip()
    tenant_id = (contract.get("contract_tenant_id") or "").strip()
    if not draft_key or not tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not ready")

    data = LexCompanionMinio().get(tenant_id, draft_key)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to read draft from storage",
        )

    suffix = (contract.get("draft_output_suffix") or ".docx").strip()
    filename = f"hop_dong_da_dien{suffix if suffix.startswith('.') else '.' + suffix}"
    media_type, _ = mimetypes.guess_type(filename)
    if not media_type:
        media_type = "application/octet-stream"

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename.replace(chr(34), chr(39))}"',
            "Cache-Control": "private, max-age=3600",
        },
    )
