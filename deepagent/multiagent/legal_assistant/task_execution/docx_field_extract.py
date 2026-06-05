from __future__ import annotations

import json
import re
from typing import Any

from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging
from deepagent.multiagent.legal_assistant.task_execution.contract_layout import similarity
from deepagent.multiagent.legal_assistant.task_execution.docx_structure import (
    blocks_to_llm_context,
    extract_structured_blocks,
    fillable_blocks,
    find_fillable_blank_matches,
    is_date_related_block,
    is_date_related_label,
)

logger = setup_logging()

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_SECTION_HEAD_RE = re.compile(
    r"^(Người|Kính gửi|Yêu cầu|Danh mục|\(Các|ĐƠN)",
    re.IGNORECASE,
)

_DOCX_EXTRACT_PROMPT = """Bạn đọc danh sách block từ mẫu văn bản pháp lý đã phân tích sẵn.

Mỗi dòng input: [block_id] (kind) fill=true/false reason=... ref=(N) | nội dung text

Nhiệm vụ: Với mỗi block có fill=true, đặt nhãn (label) thân thiện và gom nhóm HITL hợp lý.
CHỈ xử lý block fill=true đã được đánh dấu — KHÔNG tự thêm block nào.

BỎ QUA ngày/tháng/năm:
- Không tạo field cho ô ngày, tháng, năm, "ngày tháng năm sinh", dòng ký "……, ngày …… tháng …… năm……".
- Các block fill=false trong input đã được lọc sẵn — giữ nguyên, không đưa vào fields.

Trả về JSON:
{
  "fields": [
    {
      "field_key": "ten_nguoi_lam_don",
      "label": "Họ và tên người làm đơn",
      "anchor_text": "<copy nguyên văn nội dung block từ input>",
      "strategy": "<giữ nguyên strategy đã có hoặc chọn theo quy tắc dưới>",
      "required": true,
      "block_id": "<block_id từ input>"
    }
  ],
  "hitl_groups": [
    {
      "group_id": 0,
      "title": "Thông tin người làm đơn",
      "field_keys": ["ten_nguoi_lam_don"]
    }
  ]
}

Quy tắc strategy (chỉ áp dụng khi chưa có sẵn):
- replace_trailing_blank: dấu .../___ ngay sau nhãn (label:...)
- replace_placeholder_dots: cụm chấm/gạch nằm giữa hoặc đầu block
- replace_footnote_ref: dòng kết thúc bằng (N) — thay (N) bằng giá trị
- fill_table_cell: ô bảng

Nguyên tắc tuyệt đối:
- anchor_text: sao chép NGUYÊN VĂN từ nội dung block trong input — KHÔNG tự viết lại, KHÔNG rút gọn.
- block_id: PHẢI khớp chính xác với block_id trong input — KHÔNG tự đặt block_id mới.
- Chỉ đưa vào fields những block có fill=true trong input.
- KHÔNG lấy block trong mục Giải thích.
- label: ngắn gọn, tiếng Việt, mô tả đúng nội dung cần điền của block đó.
- field_key: snake_case, không dấu, duy nhất trong toàn bộ danh sách.
"""

_llm: LLMProvider | None = None


def _get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider(llm_config)
    return _llm


def _parse_json(raw: str | None) -> dict[str, Any] | None:
    if not raw or not str(raw).strip():
        return None
    text = _JSON_FENCE_RE.sub("", str(raw).strip()).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _normalize_field_key(raw: str, seen: set[str]) -> str:
    fid = re.sub(r"[^a-z0-9_]+", "_", (raw or "field").lower()).strip("_")
    if not fid or fid in seen:
        fid = f"field_{len(seen) + 1}"
    seen.add(fid)
    return fid


def _label_from_block_text(text: str, *, footnote_ref: str | None = None) -> str:
    t = (text or "").strip()
    ly_do = re.search(r"(với\s+)?lý do\s*\(\d{1,2}\)\s*:", t, re.IGNORECASE)
    if ly_do:
        return _clean_slot_label(ly_do.group(0))
    if footnote_ref and footnote_ref in t:
        t = t.replace(footnote_ref, "").strip()
    t = re.sub(r"[:：]\s*$", "", t).strip()
    if len(t) > 80:
        t = t[:77] + "..."
    return t or "Thông tin cần điền"


_BLANK_SPLIT_RE = re.compile(r"(\.{3,}|_{3,}|…{2,}|…\.(?=\s))")
_LABEL_BLANK_RE = re.compile(
    r"([^;]+?(?:\(\d{1,2}\))?:)\s*(\.{3,}|_{3,}|…{2,}|…\.(?=\s))"
)


def _fillable_blanks_in_text(text: str) -> list[re.Match[str]]:
    return find_fillable_blank_matches(text)

# Keyword cụm phân đoạn dòng nhiều chỗ trống (case-insensitive, dài trước)
_SEGMENT_KEYWORDS = [
    "số fax",
    "số điện thoại di động",
    "số điện thoại",
    "địa chỉ thư điện tử",
    "điện thoại",
    "fax",
    "email",
]


def _clean_slot_label(raw: str) -> str:
    label = re.sub(r"^[:\s,]+", "", (raw or "").strip())
    label = re.sub(r"[:：]\s*$", "", label).strip()
    return label[:80] if label else ""


def _label_before_blank(text: str, blank_start: int, *, prev_blank_end: int = 0) -> str:
    """Suy label từ đoạn text ngay trước cụm chấm/gạch."""
    segment = text[prev_blank_end:blank_start]
    segment = segment.strip(" ,;")
    if not segment or re.fullmatch(r"[.…,\s]+", segment):
        return "Địa điểm" if prev_blank_end == 0 else ""

    lower = segment.lower()
    for kw in _SEGMENT_KEYWORDS:
        idx = lower.rfind(kw)
        if idx >= 0:
            return _clean_slot_label(segment[idx:])

    m = re.search(r"([^:;]+(?:\(\d{1,2}\))?:)\s*$", segment)
    if m:
        return _clean_slot_label(m.group(1))

    tail = segment[-60:].strip()
    if tail and not re.fullmatch(r"[\(\)\d\s.…]+", tail):
        return _clean_slot_label(tail)
    return ""


def _split_labeled_blank_slots(text: str) -> list[tuple[str, int]]:
    """Tách theo pattern 'Nhãn (N): ....' lặp trên cùng dòng."""
    labeled = list(_LABEL_BLANK_RE.finditer(text))
    if len(labeled) < 2:
        return []
    result: list[tuple[str, int]] = []
    for i, m in enumerate(labeled):
        label = _clean_slot_label(m.group(1))
        if not label or re.fullmatch(r"[\(\)\d\s]+", label):
            continue
        result.append((label, i))
    return result if len(result) >= 2 else []


def _split_keyword_blank_slots(text: str) -> list[tuple[str, int]]:
    """Tách theo từ khoá (ngày/tháng/năm/điện thoại...) ngay trước mỗi cụm trống."""
    matches = _fillable_blanks_in_text(text)
    if len(matches) <= 1:
        return []

    result: list[tuple[str, int]] = []
    prev_end = 0
    for i, m in enumerate(matches):
        label = _label_before_blank(text, m.start(), prev_blank_end=prev_end)
        if not label:
            return []
        result.append((label, i))
        prev_end = m.end()

    return result if len(result) >= 2 else []


def _split_semicolon_blank_slots(text: str) -> list[tuple[str, int]]:
    """Tách theo dấu ; — mỗi đoạn có cụm trống là 1 slot."""
    matches = _fillable_blanks_in_text(text)
    if len(matches) <= 1:
        return []

    raw_parts = re.split(r"[;；]", text)
    spans: list[tuple[int, int, str]] = []
    cur = 0
    for part in raw_parts:
        spans.append((cur, cur + len(part), part))
        cur += len(part) + 1

    slot_index = 0
    result: list[tuple[str, int]] = []
    for start, end, part in spans:
        blanks_in_part = [m for m in matches if start <= m.start() < end]
        if not blanks_in_part:
            continue
        first_blank = blanks_in_part[0]
        before = _clean_slot_label(part[: first_blank.start() - start])
        if not before or re.fullmatch(r"[\(\)\d\s]+", before):
            slot_index += 1
            continue
        result.append((before, slot_index))
        slot_index += 1

    return result if len(result) >= 2 else []


def _split_multi_blank_slots(text: str) -> list[tuple[str, int]]:
    """
    Tách text có nhiều chỗ trống thành danh sách (label_context, slot_index).

    Thứ tự ưu tiên:
    1. Nhiều nhãn có dấu ':' trên cùng dòng (Chức vụ (5): ... Bộ phận (6): ...)
    2. Nhiều cụm trống với từ khoá ngay trước (ngày/tháng/năm, điện thoại/fax...)
    3. Phân đoạn theo dấu ;
    """
    matches = _fillable_blanks_in_text(text)
    if len(matches) <= 1:
        return []

    for splitter in (
        _split_labeled_blank_slots,
        _split_keyword_blank_slots,
        _split_semicolon_blank_slots,
    ):
        slots = splitter(text)
        if slots:
            slots = [(lbl, idx) for lbl, idx in slots if not is_date_related_label(lbl)]
            if slots:
                return slots
    return []


def _strategy_for_block(block: dict[str, Any], *, multi_blank: bool = False) -> str:
    reason = str(block.get("fill_reason") or "")
    if reason == "footnote_ref":
        return "replace_footnote_ref"
    if reason == "list_item":
        return "replace_list_item"
    if reason == "blank_dots":
        if multi_blank:
            return "replace_placeholder_dots_nth"
        text = str(block.get("text") or "")
        if re.search(r":\s*[.…_]{3,}", text):
            return "replace_trailing_blank"
        return "replace_placeholder_dots"
    return "replace_trailing_blank"


def _is_optional_field_label(label: str) -> bool:
    """Chỉ optional khi mẫu ghi rõ (nếu có) — còn lại blank trên dòng đều cần điền."""
    lower = (label or "").lower()
    return "nếu có" in lower or "không bắt buộc" in lower


def _anchor_for_field(text: str, strategy: str) -> str:
    """Anchor = nhãn trước placeholder; không copy cả cụm dấu chấm (tránh fill sai chỗ)."""
    if strategy in ("replace_placeholder_dots_nth", "placeholder_dots_nth"):
        return text[:200]
    matches = _fillable_blanks_in_text(text)
    if matches:
        return text[: matches[0].start()].rstrip()
    return text[:200]


def _make_location(block: dict[str, Any]) -> dict[str, Any]:
    loc: dict[str, Any] = {
        "block_id": block.get("block_id"),
        "kind": block.get("kind") or "paragraph",
    }
    if block.get("kind") == "table_cell":
        loc["table_index"] = block.get("table_index")
        loc["row"] = block.get("row")
        loc["col"] = block.get("col")
    else:
        loc["paragraph_index"] = block.get("paragraph_index")
    return loc


def extract_fields_heuristic(
    blocks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Trích field từ metadata block — không cần LLM.
    Block nhiều chỗ trống → nhiều field, mỗi field có slot_index riêng.
    """
    seen: set[str] = set()
    form_schema: list[dict[str, Any]] = []
    group_titles: list[str] = []
    group_field_keys: list[list[str]] = []
    current_group = -1

    for block in blocks:
        if block.get("in_explanation_section"):
            continue
        text = str(block.get("text") or "")
        if _SECTION_HEAD_RE.match(text):
            current_group += 1
            title = text.split(":")[0].strip()[:60] or f"Nhóm {current_group + 1}"
            group_titles.append(title)
            group_field_keys.append([])

        if not block.get("needs_fill"):
            continue

        if current_group < 0:
            current_group = 0
            group_titles.append("Thông tin chung")
            group_field_keys.append([])

        ref = block.get("footnote_ref")
        loc = _make_location(block)
        block_suffix = str(block.get("block_id") or "").replace(".", "_")

        # --- Thử tách multi-blank ---
        slots = _split_multi_blank_slots(text) if block.get("fill_reason") == "blank_dots" else []

        if slots:
            strategy = _strategy_for_block(block, multi_blank=True)
            for label_ctx, slot_idx in slots:
                slug = re.sub(r"[^a-z0-9]+", "_", label_ctx.lower()).strip("_")[:35]
                fid = _normalize_field_key(f"{slug}_s{slot_idx}_{block_suffix}", seen)
                field = {
                    "id": fid,
                    "label": label_ctx,
                    "required": not _is_optional_field_label(label_ctx),
                    "anchor_text": _anchor_for_field(text, strategy),
                    "strategy": strategy,
                    "match_strategy": strategy,
                    "slot_index": slot_idx,
                    "footnote_ref": ref,
                    "location": loc,
                    "value": "",
                }
                form_schema.append(field)
                group_field_keys[current_group].append(fid)
        else:
            label = _label_from_block_text(text, footnote_ref=ref)
            if is_date_related_block(text) or is_date_related_label(label):
                continue
            strategy = _strategy_for_block(block, multi_blank=False)
            base_key = re.sub(
                r"[^a-z0-9]+",
                "_",
                _label_from_block_text(text, footnote_ref=ref).lower(),
            ).strip("_")[:40]
            fid = _normalize_field_key(f"{base_key}_{block_suffix}", seen)
            field = {
                "id": fid,
                "label": label,
                "required": True,
                "anchor_text": _anchor_for_field(text, strategy),
                "strategy": strategy,
                "match_strategy": strategy,
                "slot_index": None,
                "footnote_ref": ref,
                "location": loc,
                "value": "",
            }
            form_schema.append(field)
            group_field_keys[current_group].append(fid)

    hitl_groups: list[dict[str, Any]] = []
    for i, keys in enumerate(group_field_keys):
        if not keys:
            continue
        hitl_groups.append(
            {
                "group_id": len(hitl_groups),
                "title": group_titles[i] if i < len(group_titles) else f"Nhóm {i + 1}",
                "field_keys": keys,
            }
        )

    if not hitl_groups and form_schema:
        keys = [str(f.get("id") or "") for f in form_schema]
        mid = max(1, len(keys) // 2)
        hitl_groups = [
            {"group_id": 0, "title": "Phần 1", "field_keys": keys[:mid]},
            {"group_id": 1, "title": "Phần 2", "field_keys": keys[mid:]},
        ]

    return form_schema, hitl_groups


def _resolve_block_for_field(
    field: dict[str, Any],
    blocks: list[dict[str, Any]],
    block_by_id: dict[str, dict[str, Any]],
    *,
    used_block_ids: set[str] | None = None,
) -> dict[str, Any] | None:
    used = used_block_ids or set()
    block_id = str(field.get("block_id") or "").strip()
    loc = field.get("location") or {}
    loc_block_id = str(loc.get("block_id") or "").strip()

    for candidate_id in (block_id, loc_block_id):
        if candidate_id and candidate_id in block_by_id:
            return block_by_id[candidate_id]

    anchor = str(field.get("anchor_text") or "").strip()
    if not anchor:
        return None

    best: dict[str, Any] | None = None
    best_score = 0.0
    for b in blocks:
        bid = str(b.get("block_id") or "")
        if bid in used:
            continue
        if b.get("in_explanation_section"):
            continue
        text = str(b.get("text") or "")
        if anchor == text:
            return b
        score = similarity(anchor, text)
        if anchor in text:
            score = max(score, 0.95)
        if score > best_score:
            best_score = score
            best = b

    if best is None or best_score < 0.55:
        return None
    return best


def resolve_field_locations(
    fields: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Gắn location cụ thể; ưu tiên block_id, tránh map trùng block."""
    block_by_id = {str(b.get("block_id") or ""): b for b in blocks}
    used_block_ids: set[str] = set()
    resolved: list[dict[str, Any]] = []

    for raw in fields:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        if isinstance(item.get("location"), dict) and item["location"].get("block_id"):
            bid = str(item["location"]["block_id"])
            if bid in block_by_id:
                used_block_ids.add(bid)
                resolved.append(item)
                continue

        block = _resolve_block_for_field(
            item, blocks, block_by_id, used_block_ids=used_block_ids
        )
        if block:
            bid = str(block.get("block_id") or "")
            used_block_ids.add(bid)
            loc: dict[str, Any] = {
                "block_id": block.get("block_id"),
                "kind": block.get("kind") or "paragraph",
            }
            if block.get("kind") == "table_cell":
                loc["table_index"] = block.get("table_index")
                loc["row"] = block.get("row")
                loc["col"] = block.get("col")
            else:
                loc["paragraph_index"] = block.get("paragraph_index")
            item["location"] = loc
        resolved.append(item)
    return resolved


def _normalize_strategy(raw: str | None, block: dict[str, Any] | None) -> str:
    s = (raw or "replace_trailing_blank").strip().lower()
    mapping = {
        "placeholder_dots": "replace_placeholder_dots",
        "explicit_placeholder": "replace_token",
        "label_only": "replace_trailing_blank",
    }
    s = mapping.get(s, s)
    if block:
        if block.get("fill_reason") == "footnote_ref":
            return "replace_footnote_ref"
        if block.get("fill_reason") == "list_item":
            return "replace_list_item"
        if block.get("kind") == "table_cell" and s == "replace_trailing_blank":
            return "fill_table_cell"
    return s


def _merge_llm_fields(
    heuristic_schema: list[dict[str, Any]],
    llm_schema: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Heuristic là nguồn sự thật theo block_id; LLM chỉ bổ sung field mới."""
    by_block: dict[str, dict[str, Any]] = {}
    for f in heuristic_schema:
        loc = f.get("location") or {}
        bid = str(loc.get("block_id") or "")
        if bid:
            by_block[bid] = f

    merged = list(heuristic_schema)
    seen_ids = {str(f.get("id") or "") for f in merged}
    for f in llm_schema:
        loc = f.get("location") or {}
        bid = str(loc.get("block_id") or "")
        if bid and bid in by_block:
            # Giữ label LLM nếu heuristic label quá generic
            existing = by_block[bid]
            if len(str(f.get("label") or "")) > len(str(existing.get("label") or "")):
                existing["label"] = f.get("label")
            continue
        fid = str(f.get("id") or "")
        if fid and fid not in seen_ids:
            merged.append(f)
            seen_ids.add(fid)
    return merged


def extract_fields_from_docx_llm(body: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Trích field schema + hitl_groups từ DOCX gốc.
    Heuristic theo block (đủ field, đúng vị trí) + LLM refine nhãn/nhóm (tuỳ chọn).
    """
    blocks = extract_structured_blocks(body)
    if not blocks:
        return [], [{"group_id": 0, "title": "Mẫu văn bản", "field_keys": []}], []

    heuristic_schema, heuristic_groups = extract_fields_heuristic(blocks)

    llm_schema: list[dict[str, Any]] = []
    llm_groups: list[dict[str, Any]] = []
    try:
        context = blocks_to_llm_context(blocks)
        raw = _get_llm().chat_text(
            [{"role": "user", "content": f"Các block mẫu:\n\n{context}"}],
            system_prompt=_DOCX_EXTRACT_PROMPT,
            max_tokens=4000,
            temperature=0.1,
        )
        data = _parse_json(raw) or {}
        raw_fields = list(data.get("fields") or [])
        llm_groups = list(data.get("hitl_groups") or [])

        block_by_id = {str(b.get("block_id") or ""): b for b in blocks}
        seen: set[str] = set()
        for f in raw_fields:
            if not isinstance(f, dict):
                continue
            fid = _normalize_field_key(str(f.get("field_key") or f.get("id") or ""), seen)
            block = _resolve_block_for_field(
                f, blocks, block_by_id, used_block_ids=set()
            )
            strategy = _normalize_strategy(str(f.get("strategy") or ""), block)
            item = {
                "id": fid,
                "label": str(f.get("label") or fid),
                "required": bool(f.get("required", True)),
                "anchor_text": str(f.get("anchor_text") or "").strip(),
                "strategy": strategy,
                "match_strategy": strategy,
                "block_id": str(f.get("block_id") or (block or {}).get("block_id") or ""),
                "value": "",
            }
            llm_schema.append(item)
        llm_schema = [
            {
                **item,
                "location": (resolve_field_locations([item], blocks)[0].get("location")),
            }
            for item in llm_schema
            if resolve_field_locations([item], blocks)[0].get("location")
        ]
    except Exception as e:
        logger.warning("extract_fields_from_docx_llm: LLM refine skipped: {}", e)

    form_schema = _merge_llm_fields(heuristic_schema, llm_schema)
    hitl_groups = heuristic_groups
    if llm_groups:
        field_ids = {str(f.get("id") or "") for f in form_schema}
        regrouped: list[dict[str, Any]] = []
        for g in llm_groups:
            if not isinstance(g, dict):
                continue
            keys = [str(k) for k in (g.get("field_keys") or []) if str(k) in field_ids]
            if keys:
                regrouped.append(
                    {
                        "group_id": int(g.get("group_id") or len(regrouped)),
                        "title": str(g.get("title") or f"Nhóm {len(regrouped) + 1}"),
                        "field_keys": keys,
                    }
                )
        if regrouped:
            hitl_groups = regrouped

    if not form_schema:
        logger.warning(
            "extract_fields_from_docx_llm: no fields; fillable_blocks={}",
            len(fillable_blocks(blocks)),
        )

    return form_schema, hitl_groups, blocks
