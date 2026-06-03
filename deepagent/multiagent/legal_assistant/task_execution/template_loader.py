from __future__ import annotations

from typing import Any

from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.db.models import DB
from deepagent.core.document_loaders.docdealing import DocDealingLoader
from deepagent.multiagent.legal_assistant.task_execution.contract_tools import (
    layout_items_to_dicts,
    load_document_bytes,
    parse_template_bytes,
)


def _normalize_suffix(suffix: str | None) -> str:
    s = (suffix or "").strip().lower()
    if s and not s.startswith("."):
        s = f".{s}"
    return s


@DB.connection_context()
def load_template_into_state(
    *,
    user_id: str,
    document_id: str,
) -> dict[str, Any]:
    doc = DocumentService.get_active_by_id_and_owner(document_id, user_id)
    if not doc or not doc.file_id:
        raise LookupError(f"Template document not found: {document_id}")
    file_row = FileService.get_or_none(id=doc.file_id)
    if not file_row or not file_row.location:
        raise LookupError("Template file record missing")

    suffix = _normalize_suffix(doc.suffix)
    if not DocDealingLoader.is_supported_suffix(suffix):
        raise ValueError(f"Unsupported template type: {suffix}")

    body = load_document_bytes(
        tenant_id=file_row.tenant_id,
        location=file_row.location,
    )
    parsed = parse_template_bytes(body, suffix=suffix)
    return {
        "template_document_id": document_id,
        "template_suffix": suffix,
        "template_markdown": parsed.markdown,
        "layout_items": layout_items_to_dicts(parsed.layout_items),
        "contract_tenant_id": file_row.tenant_id,
        "contract_kb_id": doc.kb_id,
        "contract_file_location": file_row.location,
        "_template_bytes": body,
        "doc_ids": [document_id],
    }
