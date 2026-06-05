from __future__ import annotations

from typing import Any

from api.utils.logger import setup_logging
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.task_execution.apply_field_strategies import (
    apply_field_strategies,
)
from deepagent.multiagent.legal_assistant.task_execution.contract_tools import (
    _apply_filled_values_to_markdown,
    compose_filled_docx_from_reference,
    save_draft_to_minio,
)
from deepagent.multiagent.legal_assistant.task_execution.docx_structure import (
    extract_structured_blocks,
)

logger = setup_logging()


def _reload_template_bytes_from_storage(
    state: LegalAssistantState | dict[str, Any],
) -> bytes | None:
    """Tải lại DOCX gốc khi checkpoint HITL làm mất ``_template_bytes``."""
    from deepagent.multiagent.legal_assistant.task_execution.contract_tools import (
        load_document_bytes,
    )

    tenant = str(state.get("contract_tenant_id") or "").strip()
    location = str(state.get("contract_file_location") or "").strip()
    if tenant and location:
        try:
            return load_document_bytes(tenant_id=tenant, location=location)
        except Exception as e:
            logger.warning("_reload_template_bytes_from_storage failed: {}", e)

    doc_id = str(state.get("template_document_id") or "").strip()
    user_id = str(state.get("user_id") or "").strip()
    if doc_id and user_id:
        try:
            from deepagent.multiagent.legal_assistant.task_execution.template_loader import (
                load_template_into_state,
            )

            loaded = load_template_into_state(user_id=user_id, document_id=doc_id)
            body = loaded.get("_template_bytes")
            if isinstance(body, (bytes, bytearray)):
                return bytes(body)
        except Exception as e:
            logger.warning("_reload_template_bytes_from_storage via db failed: {}", e)
    return None


def _original_template_bytes(state: LegalAssistantState | dict[str, Any]) -> bytes | None:
    """Luôn lấy bản DOCX gốc — không dùng working_docx_bytes đã patch."""
    body = state.get("_template_bytes")
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    reloaded = _reload_template_bytes_from_storage(state)
    if reloaded:
        return reloaded
    # Fallback cuối: bản đã patch (strategies phải idempotent khi re-apply).
    body = state.get("working_docx_bytes")
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    return None


def build_working_docx_bytes(state: LegalAssistantState | dict[str, Any]) -> bytes | None:
    """Patch DOCX gốc theo filled_values — nguồn preview/output cho docx_native."""
    mode = state.get("template_mode") or "markdown_reference"
    if mode != "docx_native":
        return None
    body = _original_template_bytes(state)
    if not body:
        return None
    filled = dict(state.get("filled_values") or {})
    schema = list(state.get("form_schema") or [])
    if not filled:
        return body
    return apply_field_strategies(body, filled, schema)


def build_draft_preview_markdown(state: LegalAssistantState | dict[str, Any]) -> str:
    """Preview text: DOCX native → text từ bản đã patch; markdown path → apply vào markdown."""
    docx_body = build_working_docx_bytes(state)
    if docx_body:
        blocks = extract_structured_blocks(docx_body)
        lines = [str(b.get("text") or "").strip() for b in blocks if b.get("text")]
        return "\n\n".join(lines)

    template_md = str(state.get("template_markdown") or "").strip()
    if not template_md:
        return ""
    filled = dict(state.get("filled_values") or {})
    schema = list(state.get("form_schema") or [])
    return _apply_filled_values_to_markdown(template_md, filled, schema)


def attach_draft_preview(state: LegalAssistantState) -> LegalAssistantState:
    next_state = dict(state)
    preview = build_draft_preview_markdown(next_state)
    if preview:
        next_state["draft_preview_markdown"] = preview
    working = build_working_docx_bytes(next_state)
    if working:
        next_state["working_docx_bytes"] = working
    return next_state  # type: ignore[return-value]


def persist_incremental_draft_to_storage(state: LegalAssistantState) -> LegalAssistantState:
    """
    Lưu bản DOCX nháp lên MinIO khi đã có filled_values (sau HITL / assess).
    DOCX native: patch file gốc; markdown path: soạn DOCX từ tham chiếu.
    """
    next_state = dict(state)
    filled = dict(next_state.get("filled_values") or {})
    if not filled:
        return attach_draft_preview(next_state)  # type: ignore[return-value]

    tenant = str(next_state.get("contract_tenant_id") or "").strip()
    schema = list(next_state.get("form_schema") or [])
    suffix = str(next_state.get("template_suffix") or ".docx").lower()
    kb_id = str(next_state.get("contract_kb_id") or "contract")
    doc_id = str(next_state.get("template_document_id") or "template")
    mode = next_state.get("template_mode") or "markdown_reference"

    try:
        if mode == "docx_native":
            body = build_working_docx_bytes(next_state)
            if not body or not tenant:
                return attach_draft_preview(next_state)  # type: ignore[return-value]
            next_state["working_docx_bytes"] = body
        else:
            template_md = str(next_state.get("template_markdown") or "").strip()
            if not tenant or not template_md:
                return attach_draft_preview(next_state)  # type: ignore[return-value]
            body = compose_filled_docx_from_reference(
                template_markdown=template_md,
                filled_values=filled,
                form_schema=schema,
                source_suffix=suffix,
            )

        version = int(next_state.get("draft_version") or 0) + 1
        prefix = f"{kb_id}/contract_fill/{doc_id}"
        draft_key = save_draft_to_minio(
            tenant_id=tenant,
            kb_id=kb_id,
            body=body,
            suffix=".docx",
            draft_key_prefix=prefix,
            version=version,
        )
        next_state["draft_version"] = version
        next_state["draft_object_key"] = draft_key
        next_state["draft_output_suffix"] = ".docx"
    except Exception as e:
        logger.warning("persist_incremental_draft_to_storage failed: {}", e)

    return attach_draft_preview(next_state)  # type: ignore[return-value]
