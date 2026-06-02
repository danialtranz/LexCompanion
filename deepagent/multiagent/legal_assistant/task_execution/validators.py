from __future__ import annotations

from typing import Any


def validate_document_draft(payload: dict[str, Any] | None) -> dict[str, Any]:
    draft = payload or {}
    missing: list[str] = []
    if not draft.get("title"):
        missing.append("title")
    if not draft.get("content"):
        missing.append("content")
    return {"is_valid": not missing, "missing_fields": missing}
