from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from api.apps.services.chat_service import ChatSessionService
from api.apps.services.contract_fill_service import CONTRACT_META_KEY
from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.db.models import DB
from api.utils.logger import setup_logging

logger = setup_logging()


def _filled_from_envelope(envelope: dict[str, Any]) -> dict[str, str]:
    filled = envelope.get("filled_values")
    if isinstance(filled, dict) and filled:
        return {str(k): str(v).strip() for k, v in filled.items() if v is not None and str(v).strip()}
    output = envelope.get("output")
    if isinstance(output, dict):
        out_filled = output.get("filled_values")
        if isinstance(out_filled, dict):
            return {
                str(k): str(v).strip()
                for k, v in out_filled.items()
                if v is not None and str(v).strip()
            }
    hitl = envelope.get("hitl") or {}
    if isinstance(hitl, dict):
        hitl_filled = hitl.get("filled_values")
        if isinstance(hitl_filled, dict):
            return {
                str(k): str(v).strip()
                for k, v in hitl_filled.items()
                if v is not None and str(v).strip()
            }
    return {}


def _tenant_id_for_template(*, user_id: str, template_document_id: str) -> str | None:
    doc = DocumentService.get_active_by_id_and_owner(template_document_id, user_id)
    if not doc or not doc.file_id:
        return None
    file_row = FileService.get_or_none(id=doc.file_id)
    if not file_row or not file_row.tenant_id:
        return None
    return str(file_row.tenant_id).strip() or None


def _draft_key_from_envelope(envelope: dict[str, Any]) -> str:
    direct = str(envelope.get("draft_object_key") or "").strip()
    if direct:
        return direct
    output = envelope.get("output")
    if isinstance(output, dict):
        return str(output.get("draft_object_key") or "").strip()
    return ""


def _draft_version_from_envelope(envelope: dict[str, Any]) -> int | None:
    raw = envelope.get("draft_version")
    if isinstance(raw, int):
        return raw
    output = envelope.get("output")
    if isinstance(output, dict) and isinstance(output.get("draft_version"), int):
        return output["draft_version"]
    return None


def _suffix_from_envelope(envelope: dict[str, Any]) -> str:
    direct = str(envelope.get("draft_output_suffix") or "").strip()
    if direct:
        return direct
    output = envelope.get("output")
    if isinstance(output, dict):
        return str(output.get("draft_output_suffix") or "").strip()
    return ".docx"


def _append_draft_version_history(
    contract: dict[str, Any],
    envelope: dict[str, Any],
) -> None:
    """Ghi thêm một phiên bản DOCX vào draft_versions (mỗi lần persist trên MinIO)."""
    draft_key = _draft_key_from_envelope(envelope)
    version = _draft_version_from_envelope(envelope)
    if not draft_key or version is None:
        return

    preview = _preview_from_envelope(envelope)
    suffix = _suffix_from_envelope(envelope) or str(
        contract.get("draft_output_suffix") or ".docx"
    )
    entry: dict[str, Any] = {
        "version": int(version),
        "draft_object_key": draft_key,
        "draft_output_suffix": suffix,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if preview:
        entry["draft_preview_markdown"] = preview[:12000]

    versions: list[dict[str, Any]] = [
        dict(v)
        for v in (contract.get("draft_versions") or [])
        if isinstance(v, dict)
    ]
    versions = [v for v in versions if v.get("version") != entry["version"]]
    versions.append(entry)
    versions.sort(key=lambda v: int(v.get("version") or 0))
    contract["draft_versions"] = versions


def _ensure_draft_versions_list(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Đảm bảo có draft_versions; backfill từ bản latest nếu metadata cũ."""
    versions: list[dict[str, Any]] = [
        dict(v)
        for v in (contract.get("draft_versions") or [])
        if isinstance(v, dict) and v.get("draft_object_key")
    ]
    if versions:
        return sorted(versions, key=lambda v: int(v.get("version") or 0))

    key = (contract.get("draft_object_key") or "").strip()
    ver = contract.get("draft_version")
    if key and ver is not None:
        versions = [
            {
                "version": int(ver),
                "draft_object_key": key,
                "draft_output_suffix": contract.get("draft_output_suffix") or ".docx",
                "draft_preview_markdown": contract.get("draft_preview_markdown"),
            }
        ]
        contract["draft_versions"] = versions
    return versions


def resolve_draft_version_entry(
    contract: dict[str, Any],
    version: int | None,
) -> dict[str, Any] | None:
    versions = _ensure_draft_versions_list(contract)
    if not versions:
        return None
    if version is None:
        return versions[-1]
    for entry in versions:
        if int(entry.get("version") or 0) == version:
            return entry
    return None


def _preview_from_envelope(envelope: dict[str, Any]) -> str:
    direct = str(envelope.get("draft_preview_markdown") or "").strip()
    if direct:
        return direct
    hitl = envelope.get("hitl") or {}
    if isinstance(hitl, dict):
        return str(hitl.get("draft_preview_markdown") or "").strip()
    output = envelope.get("output")
    if isinstance(output, dict):
        return str(output.get("draft_preview_markdown") or "").strip()
    return ""


@DB.connection_context()
def sync_contract_draft_from_envelope(
    *,
    session_id: str,
    user_id: str,
    envelope: dict[str, Any],
) -> None:
    """Ghi filled_values + preview + draft key vào session.metadata.contract_fill."""
    session = ChatSessionService.get_session(session_id)
    if not session or str(session.user_id) != str(user_id):
        return

    filled = _filled_from_envelope(envelope)
    preview = _preview_from_envelope(envelope)
    if not filled and not preview and not envelope.get("draft_object_key"):
        return

    meta = dict(session.metadata or {})
    contract = dict(meta.get(CONTRACT_META_KEY) or {})

    if filled:
        contract["filled_values"] = filled
    if preview:
        contract["draft_preview_markdown"] = preview

    for key in (
        "draft_object_key",
        "draft_version",
        "draft_output_suffix",
        "contract_tenant_id",
        "template_document_id",
    ):
        val = envelope.get(key)
        if val is not None and str(val).strip():
            contract[key] = val
        elif isinstance(envelope.get("output"), dict) and envelope["output"].get(key):
            contract[key] = envelope["output"][key]

    if not (contract.get("contract_tenant_id") or "").strip():
        template_id = str(contract.get("template_document_id") or "").strip()
        if template_id:
            tenant = _tenant_id_for_template(
                user_id=str(user_id),
                template_document_id=template_id,
            )
            if tenant:
                contract["contract_tenant_id"] = tenant

    _append_draft_version_history(contract, envelope)

    meta[CONTRACT_META_KEY] = contract
    session.metadata = meta
    session.save()
    logger.info(
        "sync_contract_draft: session_id={} filled_count={} has_preview={} draft_key={}",
        session_id,
        len(filled),
        bool(preview),
        bool(contract.get("draft_object_key")),
    )


@DB.connection_context()
def get_contract_draft_storage(*, session_id: str, user_id: str) -> dict[str, Any] | None:
    """Metadata contract_fill trong session (để đọc MinIO)."""
    session = ChatSessionService.get_session(session_id)
    if not session or str(session.user_id) != str(user_id):
        return None
    contract = (session.metadata or {}).get(CONTRACT_META_KEY) or {}
    if not isinstance(contract, dict):
        return None
    draft_key = (contract.get("draft_object_key") or "").strip()
    if not draft_key:
        return None
    tenant_id = (contract.get("contract_tenant_id") or "").strip()
    if not tenant_id:
        template_id = str(contract.get("template_document_id") or "").strip()
        if template_id:
            tenant_id = _tenant_id_for_template(
                user_id=str(user_id),
                template_document_id=template_id,
            ) or ""
            if tenant_id:
                contract = dict(contract)
                contract["contract_tenant_id"] = tenant_id
                meta = dict(session.metadata or {})
                meta[CONTRACT_META_KEY] = contract
                session.metadata = meta
                session.save()
    if not tenant_id:
        return None
    return dict(contract)


@DB.connection_context()
def list_contract_draft_versions(
    *,
    session_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    session = ChatSessionService.get_session(session_id)
    if not session or str(session.user_id) != str(user_id):
        return None
    contract = (session.metadata or {}).get(CONTRACT_META_KEY) or {}
    if not isinstance(contract, dict):
        return None
    versions = _ensure_draft_versions_list(contract)
    if not versions:
        return None
    latest = int(contract.get("draft_version") or versions[-1].get("version") or 0)
    items = [
        {
            "version": int(v.get("version") or 0),
            "draft_object_key": v.get("draft_object_key"),
            "draft_output_suffix": v.get("draft_output_suffix") or ".docx",
            "created_at": v.get("created_at"),
            "is_latest": int(v.get("version") or 0) == latest,
            "has_markdown_preview": bool(
                (v.get("draft_preview_markdown") or "").strip()
            ),
        }
        for v in versions
    ]
    return {
        "session_id": session_id,
        "latest_version": latest,
        "versions": items,
    }


@DB.connection_context()
def get_contract_draft_for_version(
    *,
    session_id: str,
    user_id: str,
    version: int | None = None,
) -> dict[str, Any] | None:
    """Metadata + tenant để đọc một phiên bản cụ thể (None = mới nhất)."""
    storage = get_contract_draft_storage(session_id=session_id, user_id=user_id)
    if not storage:
        return None
    entry = resolve_draft_version_entry(storage, version)
    if not entry:
        return None
    return {
        **storage,
        "draft_object_key": entry.get("draft_object_key"),
        "draft_version": entry.get("version"),
        "draft_output_suffix": entry.get("draft_output_suffix")
        or storage.get("draft_output_suffix"),
        "draft_preview_markdown": entry.get("draft_preview_markdown")
        or storage.get("draft_preview_markdown"),
    }


@DB.connection_context()
def get_contract_draft_preview(*, session_id: str, user_id: str) -> dict[str, Any] | None:
    session = ChatSessionService.get_session(session_id)
    if not session or str(session.user_id) != str(user_id):
        return None
    contract = (session.metadata or {}).get(CONTRACT_META_KEY) or {}
    if not isinstance(contract, dict):
        return None
    preview = str(contract.get("draft_preview_markdown") or "").strip()
    if not preview and not contract.get("draft_object_key"):
        return None
    return {
        "session_id": session_id,
        "draft_preview_markdown": preview,
        "filled_values": contract.get("filled_values") or {},
        "draft_version": contract.get("draft_version"),
        "draft_object_key": contract.get("draft_object_key"),
        "draft_output_suffix": contract.get("draft_output_suffix"),
        "template_document_id": contract.get("template_document_id"),
    }
