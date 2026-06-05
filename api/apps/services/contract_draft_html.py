from __future__ import annotations

import html
import io
from typing import Any

from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio

from .contract_draft_session import (
    get_contract_draft_for_version,
    list_contract_draft_versions,
)

logger = setup_logging()


def docx_bytes_to_html(body: bytes) -> str:
    """Chuyển DOCX (bản nháp từ MinIO) sang HTML cho preview editor."""
    from docx import Document

    doc = Document(io.BytesIO(body))
    blocks: list[str] = []
    for paragraph in doc.paragraphs:
        raw = paragraph.text or ""
        if not raw.strip():
            blocks.append('<p class="draft-p">&nbsp;</p>')
            continue
        safe = html.escape(raw)
        style_name = (paragraph.style.name if paragraph.style else "") or ""
        if "Heading 1" in style_name:
            blocks.append(f'<h1 class="draft-h1">{safe}</h1>')
        elif "Heading 2" in style_name:
            blocks.append(f'<h2 class="draft-h2">{safe}</h2>')
        elif "Heading 3" in style_name:
            blocks.append(f'<h3 class="draft-h3">{safe}</h3>')
        elif "Heading 4" in style_name:
            blocks.append(f'<h4 class="draft-h4">{safe}</h4>')
        else:
            blocks.append(f'<p class="draft-p">{safe}</p>')

    if not blocks:
        return '<div class="contract-draft-html"><p class="draft-p"></p></div>'
    return f'<div class="contract-draft-html">{"".join(blocks)}</div>'


def load_contract_draft_bytes(
    *,
    session_id: str,
    user_id: str,
    version: int | None = None,
) -> bytes | None:
    storage = get_contract_draft_for_version(
        session_id=session_id,
        user_id=user_id,
        version=version,
    )
    if not storage:
        return None
    draft_key = (storage.get("draft_object_key") or "").strip()
    tenant_id = (storage.get("contract_tenant_id") or "").strip()
    if not draft_key or not tenant_id:
        return None
    data = LexCompanionMinio().get(tenant_id, draft_key)
    return data if data else None


def get_contract_draft_html_preview(
    *,
    session_id: str,
    user_id: str,
    version: int | None = None,
) -> dict[str, Any] | None:
    """
    Đọc DOCX nháp từ MinIO và trả HTML + metadata.
    ``version`` None = phiên bản mới nhất.
    """
    storage = get_contract_draft_for_version(
        session_id=session_id,
        user_id=user_id,
        version=version,
    )
    if not storage:
        return None

    body = load_contract_draft_bytes(
        session_id=session_id,
        user_id=user_id,
        version=version,
    )
    if not body:
        return None

    try:
        preview_html = docx_bytes_to_html(body)
    except Exception as e:
        logger.error(
            "docx_bytes_to_html failed session_id={} version={}: {}",
            session_id,
            version,
            e,
        )
        return None

    return {
        "session_id": session_id,
        "html": preview_html,
        "draft_version": storage.get("draft_version"),
        "draft_object_key": storage.get("draft_object_key"),
        "draft_output_suffix": storage.get("draft_output_suffix"),
        "source": "minio_docx",
    }


def get_contract_draft_versions_list(
    *,
    session_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    return list_contract_draft_versions(session_id=session_id, user_id=user_id)
