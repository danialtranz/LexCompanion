from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging

logger = setup_logging().bind(tag="hitl")

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_llm: LLMProvider | None = None

_LEGAL_HITL_ASSESSMENT_PROMPT = """Bạn là bộ đánh giá sau bước truy xuất tài liệu (RAG hoặc web) cho chatbot tư vấn pháp luật Việt Nam.

Bạn nhận: câu hỏi user (đã làm rõ), câu trả lời RAG, tóm tắt căn cứ pháp luật trích được, và (nếu có) lịch sử chat.

Phải phân tích HAI việc tách bạch:

1) **Đủ căn cứ pháp luật trong RAG chưa** (`is_context_sufficient`):
   - true khi đã có văn bản/điều khoản liên quan để tư vấn về vấn đề user hỏi.
   - false khi RAG không có luật liên quan hoặc answer trống/không căn cứ.

2) **Cần thêm thông tin cá nhân/hoàn cảnh từ user không** (`needs_user_clarification`):
   - Pháp luật thường phụ thuộc đối tượng áp dụng, loại hành vi, mức độ, tình tiết (xe máy/ô tô; đã vi phạm hay chưa; tái phạm; thương tích...).
   - true khi: đã có khung pháp lý trong RAG nhưng CHƯA đủ dữ kiện để chốt mức xử phạt/kết luận cho ĐÚNG trường hợp của user.
   - Ví dụ: "Vượt đèn đỏ phạt bao nhiêu?" — RAG có mức phạt xe máy và ô tô khác nhau → needs_user_clarification=true.
   - false khi user đã nêu đủ trong câu hỏi hoặc lịch sử chat gần đây, HOẶC câu hỏi chỉ cần giải thích chung không phụ thuộc hoàn cảnh.

Bạn PHẢI trả về đúng JSON:
{
  "is_context_sufficient": true,
  "needs_user_clarification": false,
  "missing_facts": ["..."],
  "clarification_questions": ["..."],
  "partial_answer_preface": "...",
  "insufficiency_reason": "...",
  "assessment_reason": "..."
}

Quy tắc:
- missing_facts: nhãn ngắn các yếu tố còn thiếu (tiếng Việt).
- clarification_questions: 1–4 câu hỏi cụ thể, lịch sự, giúp áp dụng luật vào case của user; không hỏi thứ đã có trong lịch sử.
- partial_answer_preface: 2–4 câu tóm tắt những gì RAG đã cho biết (khung pháp lý chung), KHÔNG chốt số tiền/mức phạt cụ thể nếu còn thiếu dữ kiện; có thể nhắc "tùy loại xe/tình tiết".
- Nếu needs_user_clarification=true thì is_context_sufficient vẫn có thể true (đã có luật, thiếu facts user).
- Nếu thiếu luật trong RAG: is_context_sufficient=false, needs_user_clarification=false.
- insufficiency_reason: dùng khi cần tìm thêm tài liệu (RAG/web), không nhầm với thiếu facts user.
"""

_WEB_HITL_ASSESSMENT_PROMPT = """Bạn là bộ đánh giá sau bước tổng hợp câu trả lời từ tìm kiếm web (+ có thể có RAG nội bộ) cho chatbot pháp luật Việt Nam.

Phân tích tương tự RAG:
1) `is_context_sufficient`: thông tin web/RAG đã đủ để trả lời câu hỏi chưa (có căn cứ, không chỉ đoán).
2) `needs_user_clarification`: đã có khung thông tin nhưng cần thêm hoàn cảnh cá nhân user để chốt mức phạt/kết luận đúng case.

Trả về cùng schema JSON như đánh giá RAG. Nếu kết quả web mơ hồ, thiếu nguồn, hoặc không trả lời trực tiếp → is_context_sufficient=false.
"""


class HitlAssessment(TypedDict):
    is_context_sufficient: bool
    needs_user_clarification: bool
    missing_facts: list[str]
    clarification_questions: list[str]
    partial_answer_preface: str
    insufficiency_reason: str
    assessment_reason: str


def _get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider(llm_config)
    return _llm


def _format_chat_history(chat_history: list[dict[str, Any]] | None, limit: int = 6) -> str:
    if not chat_history:
        return ""
    lines: list[str] = []
    for item in chat_history[-limit:]:
        role = str(item.get("role") or "user").strip()
        content = str(item.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _web_results_digest(
    web_results: list[dict[str, Any]] | None, limit: int = 6
) -> list[dict[str, str]]:
    digest: list[dict[str, str]] = []
    for item in (web_results or [])[:limit]:
        if not isinstance(item, dict):
            continue
        digest.append(
            {
                "title": str(item.get("title") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "snippet": str(item.get("content") or "")[:400],
            }
        )
    return digest


def _references_digest(references: list[dict[str, Any]] | None, limit: int = 6) -> list[dict[str, str]]:
    digest: list[dict[str, str]] = []
    for ref in (references or [])[:limit]:
        if not isinstance(ref, dict):
            continue
        digest.append(
            {
                "ieee": str(ref.get("ieee") or "").strip(),
                "topic_title": str(ref.get("topic_title") or "").strip(),
                "subject_title": str(ref.get("subject_title") or "").strip(),
                "article_title": str(ref.get("article_title") or "").strip(),
                "snippet": str(ref.get("content_text") or ref.get("content") or "")[:400],
            }
        )
    return digest


def _default_assessment(
    *,
    is_context_sufficient: bool,
    needs_user_clarification: bool = False,
    insufficiency_reason: str = "",
    assessment_reason: str = "",
) -> HitlAssessment:
    return {
        "is_context_sufficient": is_context_sufficient,
        "needs_user_clarification": needs_user_clarification,
        "missing_facts": [],
        "clarification_questions": [],
        "partial_answer_preface": "",
        "insufficiency_reason": insufficiency_reason,
        "assessment_reason": assessment_reason,
    }


def _parse_assessment(raw: str | None) -> HitlAssessment | None:
    if not raw or not str(raw).strip():
        return None
    cleaned = _JSON_FENCE_RE.sub("", str(raw).strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("assess_rag_for_hitl: invalid json: {}", cleaned[:500])
        return None
    if not isinstance(data, dict):
        return None

    questions: list[str] = []
    for q in data.get("clarification_questions") or []:
        text = str(q or "").strip()
        if text and text not in questions:
            questions.append(text)

    missing: list[str] = []
    for m in data.get("missing_facts") or []:
        text = str(m or "").strip()
        if text and text not in missing:
            missing.append(text)

    return {
        "is_context_sufficient": bool(data.get("is_context_sufficient", False)),
        "needs_user_clarification": bool(data.get("needs_user_clarification", False)),
        "missing_facts": missing,
        "clarification_questions": questions,
        "partial_answer_preface": str(data.get("partial_answer_preface") or "").strip(),
        "insufficiency_reason": str(data.get("insufficiency_reason") or "").strip(),
        "assessment_reason": str(data.get("assessment_reason") or "").strip(),
    }


def assess_rag_for_hitl(
    *,
    user_query: str,
    resolved_user_request: str,
    rag_answer: str,
    references: list[dict[str, Any]] | None = None,
    chat_history: list[dict[str, Any]] | None = None,
) -> HitlAssessment:
    """Đánh giá sau RAG: đủ căn cứ pháp luật chưa và có cần hỏi thêm user để áp dụng đúng case không."""
    answer = (rag_answer or "").strip()
    if not answer:
        return _default_assessment(
            is_context_sufficient=False,
            insufficiency_reason="RAG không trả lời hoặc answer rỗng.",
            assessment_reason="empty rag answer",
        )

    payload = {
        "user_query": (user_query or "").strip(),
        "resolved_user_request": (resolved_user_request or user_query or "").strip(),
        "rag_answer": answer,
        "references_digest": _references_digest(references),
        "chat_history": _format_chat_history(chat_history),
    }
    raw = _get_llm().chat_text(
        [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        system_prompt=_LEGAL_HITL_ASSESSMENT_PROMPT,
        temperature=0.0,
        max_tokens=520,
    )
    parsed = _parse_assessment(raw)
    if parsed is None:
        logger.warning("assess_rag_for_hitl: fallback to permissive sufficient")
        return _default_assessment(
            is_context_sufficient=True,
            assessment_reason="llm parse failed",
        )

    logger.info(
        "assess_rag_for_hitl: sufficient={} needs_clarification={} questions={}",
        parsed["is_context_sufficient"],
        parsed["needs_user_clarification"],
        len(parsed["clarification_questions"]),
    )
    return parsed


def assess_web_for_hitl(
    *,
    user_query: str,
    resolved_user_request: str,
    synthesized_answer: str,
    references: list[dict[str, Any]] | None = None,
    web_results: list[dict[str, Any]] | None = None,
    chat_history: list[dict[str, Any]] | None = None,
) -> HitlAssessment:
    """Đánh giá sau tổng hợp web: đủ thông tin trả lời chưa và có cần hỏi thêm user không."""
    answer = (synthesized_answer or "").strip()
    if not answer:
        return _default_assessment(
            is_context_sufficient=False,
            insufficiency_reason="Tổng hợp web không tạo được câu trả lời.",
            assessment_reason="empty web synthesis",
        )

    payload = {
        "user_query": (user_query or "").strip(),
        "resolved_user_request": (resolved_user_request or user_query or "").strip(),
        "synthesized_answer": answer,
        "references_digest": _references_digest(references),
        "web_results_digest": _web_results_digest(web_results),
        "chat_history": _format_chat_history(chat_history),
    }
    raw = _get_llm().chat_text(
        [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        system_prompt=_WEB_HITL_ASSESSMENT_PROMPT,
        temperature=0.0,
        max_tokens=520,
    )
    parsed = _parse_assessment(raw)
    if parsed is None:
        return _default_assessment(
            is_context_sufficient=False,
            insufficiency_reason="Không đánh giá được chất lượng kết quả web.",
            assessment_reason="llm parse failed",
        )

    logger.info(
        "assess_web_for_hitl: sufficient={} needs_clarification={} questions={}",
        parsed["is_context_sufficient"],
        parsed["needs_user_clarification"],
        len(parsed["clarification_questions"]),
    )
    return parsed


def compose_clarification_answer(assessment: HitlAssessment) -> str:
    """Ghép câu trả lời khi cần user bổ sung hoàn cảnh."""
    parts: list[str] = []
    preface = (assessment.get("partial_answer_preface") or "").strip()
    if preface:
        parts.append(preface)

    questions = assessment.get("clarification_questions") or []
    if questions:
        parts.append(
            "Để áp dụng đúng quy định vào trường hợp của bạn, bạn vui lòng cho biết thêm:"
        )
        for i, q in enumerate(questions, start=1):
            parts.append(f"{i}. {q}")

    if not parts:
        parts.append(
            "Tôi cần thêm một vài thông tin về hoàn cảnh cụ thể của bạn "
            "để xác định chính xác quy định áp dụng. Bạn mô tả thêm chi tiết được không?"
        )
    return "\n\n".join(parts)
