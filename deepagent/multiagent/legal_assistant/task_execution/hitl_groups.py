from __future__ import annotations

from typing import Any

from deepagent.multiagent.legal_assistant.task_execution.docx_structure import excerpt_for_group


def map_fields_to_group_indices(
    form_schema: list[dict[str, Any]],
    hitl_groups: list[dict[str, Any]],
) -> dict[str, int]:
    """Gán field id → chỉ số nhóm HITL (không dựa markdown chunk)."""
    result: dict[str, int] = {}
    for gi, group in enumerate(hitl_groups):
        for key in group.get("field_keys") or []:
            result[str(key)] = gi
    n_groups = max(len(hitl_groups), 1)
    for i, field in enumerate(form_schema):
        fid = str(field.get("id") or "").strip()
        if not fid or fid in result:
            continue
        result[fid] = min(n_groups - 1, (i * n_groups) // max(len(form_schema), 1))
    return result


def group_excerpts(
    hitl_groups: list[dict[str, Any]],
    structured_blocks: list[dict[str, Any]],
    form_schema: list[dict[str, Any]],
) -> list[str]:
    """Text excerpt mỗi nhóm — dùng cho assess/HITL, không phải bản mutate."""
    excerpts: list[str] = []
    for group in hitl_groups:
        keys = {str(k) for k in (group.get("field_keys") or [])}
        title = str(group.get("title") or "").strip()
        body = excerpt_for_group(structured_blocks, keys, form_schema)
        if title and body:
            excerpts.append(f"## {title}\n\n{body}")
        elif body:
            excerpts.append(body)
        elif title:
            excerpts.append(title)
        else:
            excerpts.append("")
    return excerpts or [""]


def fields_for_group(
    form_schema: list[dict[str, Any]],
    field_group_index: dict[str, int],
    group_index: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in form_schema:
        fid = str(f.get("id") or "")
        if field_group_index.get(fid, 0) == group_index:
            out.append(f)
    return out


def is_group_complete(
    form_schema: list[dict[str, Any]],
    field_group_index: dict[str, int],
    group_index: int,
    filled_values: dict[str, str],
) -> bool:
    for f in form_schema:
        fid = str(f.get("id") or "")
        if field_group_index.get(fid, 0) != group_index:
            continue
        if not f.get("required", True):
            continue
        if not (filled_values.get(fid) or "").strip():
            return False
    return True
