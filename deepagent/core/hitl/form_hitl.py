from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging
from deepagent.core.hitl.hitl import compose_clarification_answer

logger = setup_logging().bind(tag="form_hitl")

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_llm: LLMProvider | None = None

_FORM_HITL_PROMPT = """Bạn đánh giá tiến độ điền mẫu hợp đồng/văn bản.

Input: danh sách field (id, label, required, giá trị hiện tại), câu hỏi/yêu cầu mới của user, lịch sử chat ngắn.

Nhiệm vụ:
1) Xác định field nào user vừa cung cấp giá trị (cập nhật vào proposed_values).
2) Field required nào vẫn thiếu (missing_field_ids).
3) Có cần hỏi user thêm không (needs_user_clarification).
4) Viết 1-3 câu hỏi cụ thể (clarification_questions) — chỉ hỏi field còn thiếu, ưu tiên cùng nhóm (ví dụ thông tin Bên A).
5) partial_answer_preface: tóm tắt ngắn đã điền được gì.

Trả về JSON:
{
  "needs_user_clarification": true,
  "missing_field_ids": ["..."],
  "missing_facts": ["nhãn field thiếu"],
  "clarification_questions": ["..."],
  "partial_answer_preface": "...",
  "proposed_values": {"field_id": "giá trị"},
  "assessment_reason": "...",
  "is_complete": false
}

Quy tắc:
- is_complete=true chỉ khi mọi field required đã có giá trị hợp lệ (không rỗng).
- needs_user_clarification=true khi còn required thiếu.
- proposed_values: chỉ field user vừa nêu rõ trong tin nhắn mới; không đoán.
- Tiếng Việt.
"""


class FormHitlAssessment(TypedDict, total=False):
    needs_user_clarification: bool
    missing_field_ids: list[str]
    missing_facts: list[str]
    clarification_questions: list[str]
    partial_answer_preface: str
    proposed_values: dict[str, str]
    assessment_reason: str
    is_complete: bool


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


def _format_fields_summary(form_schema: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for f in form_schema:
        fid = f.get("id") or ""
        label = f.get("label") or fid
        req = "required" if f.get("required") else "optional"
        val = (f.get("value") or "").strip()
        status = "filled" if val else "empty"
        lines.append(f"- {fid} ({label}) [{req}] [{status}]: {val or '(trống)'}")
    return "\n".join(lines) if lines else "(không có field)"


def assess_form_for_hitl(
    *,
    user_message: str,
    form_schema: list[dict[str, Any]],
    filled_values: dict[str, str],
    chat_history: list[dict[str, Any]] | None = None,
) -> FormHitlAssessment:
    """Đánh giá field thiếu và trích giá trị mới từ tin nhắn user."""
    schema_for_llm = []
    for f in form_schema:
        fid = str(f.get("id") or "")
        schema_for_llm.append(
            {
                "id": fid,
                "label": f.get("label") or fid,
                "required": bool(f.get("required", True)),
                "value": filled_values.get(fid) or f.get("value") or "",
            }
        )

    history_lines: list[str] = []
    for item in (chat_history or [])[-6:]:
        role = str(item.get("role") or "user")
        content = str(item.get("content") or "").strip()
        if content:
            history_lines.append(f"{role}: {content}")

    user_content = (
        f"Tin nhắn mới của user:\n{user_message.strip()}\n\n"
        f"Các field:\n{_format_fields_summary(schema_for_llm)}\n"
    )
    if history_lines:
        user_content += "\nLịch sử chat gần đây:\n" + "\n".join(history_lines)

    raw = _get_llm().chat_text(
        [{"role": "user", "content": user_content}],
        system_prompt=_FORM_HITL_PROMPT,
        max_tokens=1500,
        temperature=0.2,
    )
    parsed = _parse_json(raw)
    if not parsed:
        return _fallback_assessment(form_schema, filled_values)

    proposed = parsed.get("proposed_values") or {}
    if isinstance(proposed, dict):
        clean_proposed = {
            str(k): str(v).strip()
            for k, v in proposed.items()
            if v is not None and str(v).strip()
        }
    else:
        clean_proposed = {}

    merged = {**filled_values, **clean_proposed}
    missing_ids = list(parsed.get("missing_field_ids") or [])
    if not missing_ids:
        missing_ids = [
            str(f["id"])
            for f in schema_for_llm
            if f.get("required") and not (merged.get(str(f["id"])) or "").strip()
        ]

    is_complete = bool(parsed.get("is_complete"))
    if not is_complete:
        is_complete = not any(
            f.get("required")
            and not (merged.get(str(f.get("id") or "")) or "").strip()
            for f in schema_for_llm
        )

    needs = bool(parsed.get("needs_user_clarification", not is_complete))
    if is_complete:
        needs = False

    missing_facts = list(parsed.get("missing_facts") or [])
    if not missing_facts:
        id_to_label = {str(f["id"]): str(f.get("label") or f["id"]) for f in schema_for_llm}
        missing_facts = [id_to_label.get(mid, mid) for mid in missing_ids]

    questions = list(parsed.get("clarification_questions") or [])
    if needs and not questions and missing_facts:
        questions = [f"Bạn vui lòng cho biết: {missing_facts[0]}?"]
        if len(missing_facts) > 1:
            questions.append(f"Thêm: {missing_facts[1]}?")

    return FormHitlAssessment(
        needs_user_clarification=needs,
        missing_field_ids=missing_ids,
        missing_facts=missing_facts,
        clarification_questions=questions[:4],
        partial_answer_preface=str(parsed.get("partial_answer_preface") or "").strip(),
        proposed_values=clean_proposed,
        assessment_reason=str(parsed.get("assessment_reason") or ""),
        is_complete=is_complete,
    )


def _fallback_assessment(
    form_schema: list[dict[str, Any]],
    filled_values: dict[str, str],
) -> FormHitlAssessment:
    missing_ids = [
        str(f.get("id") or "")
        for f in form_schema
        if f.get("required") and not (filled_values.get(str(f.get("id") or "")) or "").strip()
    ]
    id_to_label = {str(f.get("id") or ""): str(f.get("label") or f.get("id")) for f in form_schema}
    missing_facts = [id_to_label.get(i, i) for i in missing_ids]
    is_complete = not missing_ids
    questions = (
        [f"Bạn vui lòng cung cấp: {missing_facts[0]}."]
        if missing_facts
        else []
    )
    return FormHitlAssessment(
        needs_user_clarification=not is_complete,
        missing_field_ids=missing_ids,
        missing_facts=missing_facts,
        clarification_questions=questions,
        partial_answer_preface="Đang thu thập thông tin để điền mẫu hợp đồng.",
        proposed_values={},
        assessment_reason="llm parse failed — heuristic fallback",
        is_complete=is_complete,
    )


def compose_form_clarification_answer(assessment: FormHitlAssessment) -> str:
    """Ghép câu trả lời HITL cho form fill (tương thích HitlAssessment)."""
    hitl_compat = {
        "partial_answer_preface": assessment.get("partial_answer_preface") or "",
        "clarification_questions": assessment.get("clarification_questions") or [],
    }
    return compose_clarification_answer(hitl_compat)  # type: ignore[arg-type]
