from __future__ import annotations

import mimetypes
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import Response

from api.apps.services.contract_draft_html import (
    get_contract_draft_html_preview,
    get_contract_draft_versions_list,
    load_contract_draft_bytes,
)
from api.apps.services.contract_draft_session import (
    get_contract_draft_for_version,
    get_contract_draft_preview,
)
from api.db.models import Users


def fetch_contract_draft_preview(*, user: Users, session_id: str) -> dict:
    """JSON preview markdown đã điền (cho editor phía FE)."""
    data = get_contract_draft_preview(session_id=session_id, user_id=user.id)
    if not data:
        return {"code": 404, "msg": "No draft preview for session", "data": None}
    return {"code": 200, "msg": "OK", "data": data}


def fetch_contract_draft_versions(*, user: Users, session_id: str) -> dict:
    data = get_contract_draft_versions_list(session_id=session_id, user_id=user.id)
    if not data:
        return {"code": 404, "msg": "No draft versions for session", "data": None}
    return {"code": 200, "msg": "OK", "data": data}


def fetch_contract_draft_preview_html(
    *,
    user: Users,
    session_id: str,
    version: int | None = None,
) -> dict:
    """HTML preview từ DOCX nháp trên MinIO."""
    data = get_contract_draft_html_preview(
        session_id=session_id,
        user_id=user.id,
        version=version,
    )
    if not data:
        return {
            "code": 404,
            "msg": "No draft DOCX on storage for session",
            "data": None,
        }
    return {"code": 200, "msg": "OK", "data": data}


def _stream_contract_draft_bytes(
    *,
    user: Users,
    session_id: str,
    version: int | None,
    inline: bool,
) -> Response:
    contract = get_contract_draft_for_version(
        session_id=session_id,
        user_id=user.id,
        version=version,
    )
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not ready")

    data = load_contract_draft_bytes(
        session_id=session_id,
        user_id=user.id,
        version=version,
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to read draft from storage",
        )

    ver = int(contract.get("draft_version") or 0)
    suffix = (contract.get("draft_output_suffix") or ".docx").strip()
    filename = f"hop_dong_da_dien_v{ver}{suffix if suffix.startswith('.') else '.' + suffix}"
    media_type, _ = mimetypes.guess_type(filename)
    if not media_type:
        media_type = "application/octet-stream"

    safe_name = filename.replace(chr(34), chr(39))
    disposition = "inline" if inline else "attachment"
    draft_key = str(contract.get("draft_object_key") or "").strip()

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{safe_name}"',
            "Cache-Control": "private, max-age=300",
            "X-Draft-Version": str(ver),
            "X-Draft-Object-Key": draft_key,
            "X-Draft-Output-Suffix": suffix,
        },
    )


def stream_contract_draft_preview_binary(
    *,
    user: Users,
    session_id: str,
    version: int | None = None,
) -> Response:
    """Trả DOCX nháp từ MinIO dạng binary — FE render trực tiếp (inline)."""
    return _stream_contract_draft_bytes(
        user=user,
        session_id=session_id,
        version=version,
        inline=True,
    )


def stream_contract_draft(
    *,
    user: Users,
    session_id: str,
    version: int | None = None,
) -> Response:
    return _stream_contract_draft_bytes(
        user=user,
        session_id=session_id,
        version=version,
        inline=False,
    )
