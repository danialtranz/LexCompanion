from __future__ import annotations

import re
from typing import Any

DEFAULT_MAX_CHUNK_CHARS = 2500


def split_markdown_into_chunks(
    markdown: str,
    *,
    max_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> list[str]:
    """
    Cắt markdown thành các đoạn theo đoạn văn (\\n\\n), gom đến ~max_chars mỗi chunk.
    Không dùng nhãn semantic (Bên A, Phần I).
    """
    text = (markdown or "").strip()
    if not text:
        return [""]

    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    if not paragraphs:
        return [text[:max_chars] if len(text) > max_chars else text]

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    for para in paragraphs:
        sep = 2 if buf else 0
        add_len = len(para) + sep
        if buf and buf_len + add_len > max_chars:
            chunks.append("\n\n".join(buf))
            buf = [para]
            buf_len = len(para)
        else:
            buf.append(para)
            buf_len += add_len

    if buf:
        chunks.append("\n\n".join(buf))

    return chunks or [text]


def _chunk_spans_in_markdown(markdown: str, chunks: list[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    pos = 0
    for chunk in chunks:
        if not chunk:
            spans.append((pos, pos))
            continue
        needle = chunk[: min(120, len(chunk))]
        idx = markdown.find(needle, pos) if needle else -1
        if idx < 0:
            idx = pos
        start = idx
        end = min(len(markdown), start + len(chunk))
        spans.append((start, end))
        pos = max(pos, end)
    return spans


def _chunk_index_for_offset(offset: int, spans: list[tuple[int, int]]) -> int:
    if not spans:
        return 0
    for i, (start, end) in enumerate(spans):
        if start <= offset < end:
            return i
    return len(spans) - 1


def _find_field_position(markdown: str, field: dict[str, Any]) -> int:
    anchor = str(field.get("anchor_text") or "").strip()
    if anchor and anchor in markdown:
        return markdown.index(anchor)
    label = str(field.get("label") or "").strip()
    if len(label) >= 4 and label in markdown:
        return markdown.index(label)
    fid = str(field.get("id") or "").replace("_", " ")
    if len(fid) >= 4 and fid in markdown.lower():
        return markdown.lower().index(fid)
    return -1


def map_fields_to_chunk_indices(
    form_schema: list[dict[str, Any]],
    markdown: str,
    chunks: list[str],
) -> dict[str, int]:
    """Gán mỗi field id → chỉ số chunk (theo vị trí anchor trong markdown hoặc thứ tự field)."""
    if not chunks:
        return {}
    spans = _chunk_spans_in_markdown(markdown, chunks)
    n_chunks = len(chunks)
    n_fields = max(len(form_schema), 1)
    result: dict[str, int] = {}

    for i, field in enumerate(form_schema):
        fid = str(field.get("id") or "").strip()
        if not fid:
            continue
        pos = _find_field_position(markdown, field)
        if pos >= 0:
            result[fid] = _chunk_index_for_offset(pos, spans)
        else:
            result[fid] = min(n_chunks - 1, (i * n_chunks) // n_fields)

    return result


def fields_for_chunk(
    form_schema: list[dict[str, Any]],
    field_chunk_index: dict[str, int],
    chunk_index: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in form_schema:
        fid = str(f.get("id") or "")
        if field_chunk_index.get(fid, 0) == chunk_index:
            out.append(f)
    return out


def all_required_filled(
    form_schema: list[dict[str, Any]],
    filled_values: dict[str, str],
) -> bool:
    for f in form_schema:
        fid = str(f.get("id") or "")
        if not fid or not f.get("required", True):
            continue
        if not (filled_values.get(fid) or "").strip():
            return False
    return True


def is_chunk_complete(
    form_schema: list[dict[str, Any]],
    field_chunk_index: dict[str, int],
    chunk_index: int,
    filled_values: dict[str, str],
) -> bool:
    for f in form_schema:
        fid = str(f.get("id") or "")
        if field_chunk_index.get(fid, 0) != chunk_index:
            continue
        if not f.get("required", True):
            continue
        if not (filled_values.get(fid) or "").strip():
            return False
    return True


def refine_assessment_for_chunk(
    assessment: dict[str, Any],
    *,
    form_schema: list[dict[str, Any]],
    field_chunk_index: dict[str, int],
    chunk_index: int,
    merged_values: dict[str, str],
) -> dict[str, Any]:
    """Giữ missing/proposed chỉ thuộc chunk; is_complete = chunk hiện tại đủ required."""
    chunk_ids = {
        str(f.get("id") or "")
        for f in form_schema
        if field_chunk_index.get(str(f.get("id") or ""), 0) == chunk_index
    }
    out = dict(assessment)
    missing = [
        mid
        for mid in list(assessment.get("missing_field_ids") or [])
        if mid in chunk_ids
    ]
    for f in form_schema:
        fid = str(f.get("id") or "")
        if fid not in chunk_ids or not f.get("required", True):
            continue
        if not (merged_values.get(fid) or "").strip() and fid not in missing:
            missing.append(fid)

    proposed = assessment.get("proposed_values") or {}
    if isinstance(proposed, dict):
        proposed = {k: v for k, v in proposed.items() if k in chunk_ids}
    else:
        proposed = {}

    id_to_label = {
        str(f.get("id") or ""): str(f.get("label") or f.get("id")) for f in form_schema
    }
    missing_facts = [id_to_label.get(mid, mid) for mid in missing]

    out["missing_field_ids"] = missing
    out["missing_facts"] = missing_facts
    out["proposed_values"] = proposed
    out["needs_user_clarification"] = bool(missing)
    out["is_complete"] = not missing
    if missing and not out.get("clarification_questions"):
        out["clarification_questions"] = [
            f"Bạn vui lòng cho biết: {missing_facts[0]}?"
        ]
    return out
