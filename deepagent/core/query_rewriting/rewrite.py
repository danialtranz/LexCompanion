from __future__ import annotations

import json
import os
import re
from typing import Any, TypedDict

from api.apps.services.legal_service import LegalSubjectService, LegalTopicService
from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging

logger = setup_logging().bind(tag="requery_for_rag")

_RAG_REQUERY_DEBUG = os.getenv("RAG_REQUERY_DEBUG", "").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_llm: LLMProvider | None = None

_USER_INTENT_SYSTEM_PROMPT = """Bạn là trợ lý suy luận ý định người dùng trong hội thoại pháp lý dài.
Nhiệm vụ: đọc lịch sử chat + tin nhắn hiện tại, rồi diễn đạt rõ người dùng THỰC SỰ muốn gì ở lượt này.

Đây KHÔNG phải bước viết lại truy vấn để tối ưu RAG/tìm kiếm. Không thêm từ khóa tra cứu, không mở rộng chủ đề ngoài ý người dùng.

Bạn PHẢI trả về đúng JSON:
{
  "clarified_request": "...",
  "intent_reason": "..."
}

Quy tắc:
- Giải quyết đại từ/mệnh lệnh mơ hồ ("sửa lại", "làm lại", "cái đó", "như vậy không được", "đổi giúp") bằng cách nhìn lại ngữ cảnh gần nhất: họ muốn sửa/đổi/làm lại CÁI GÌ, theo hướng nào.
- clarified_request là một câu yêu cầu độc lập, đủ ngữ cảnh để agent hiểu và xử lý (hỏi, soạn lại, chỉnh sửa, bổ sung, từ chối, v.v.).
- Giữ đúng mục tiêu pháp lý và phạm vi người dùng đã nêu; không bịa thêm dữ kiện không có trong lịch sử.
- Nếu tin nhắn hiện tại đã rõ và tự đủ nghĩa thì clarified_request gần như giữ nguyên nội dung đó.
- intent_reason ngắn gọn: giải thích vì sao diễn giải như vậy (tham chiếu đoạn hội thoại nào).
"""

_RAG_REQUERY_SYSTEM_PROMPT = """
Bạn là bộ lập kế hoạch truy vấn RAG cho corpus pháp luật Việt Nam.

Input: yêu cầu đã làm rõ của user + catalog topic/subject.

Nhiệm vụ:
1. Chọn topic phù hợp nhất.
2. Sinh 3–6 search_query dùng để hybrid search trong corpus pháp luật.
3. search_query KHÔNG phải câu trả lời, KHÔNG phải câu hỏi hội thoại, KHÔNG dùng lời lịch sự như "xin vui lòng", "cho tôi biết".

Nguyên tắc pháp lý bắt buộc khi requery:
- Luôn xác định hoặc mở rộng theo ĐỐI TƯỢNG ÁP DỤNG: cá nhân/tổ chức, người điều khiển phương tiện, người chưa đủ tuổi nếu liên quan.
- Luôn xác định hoặc mở rộng theo PHƯƠNG TIỆN/HÀNH VI: ô tô, xe máy, xe đạp điện, vượt đèn đỏ, không chấp hành hiệu lệnh đèn tín hiệu giao thông.
- Nếu user hỏi về "phạt", phải sinh query bao phủ:
  + mức phạt tiền;
  + hình phạt bổ sung;
  + tước giấy phép lái xe;
  + trừ điểm giấy phép lái xe nếu pháp luật hiện hành có;
  + tình tiết tăng nặng/hậu quả như gây tai nạn giao thông.
- Nếu user chưa nói rõ phương tiện hoặc tình huống, KHÔNG hỏi lại trong requery; hãy sinh nhiều query theo các khả năng phổ biến.
- Ưu tiên thuật ngữ giống văn bản pháp luật: "không chấp hành hiệu lệnh của đèn tín hiệu giao thông", "người điều khiển xe", "xử phạt vi phạm hành chính", "hình thức xử phạt bổ sung".
- search_queries phải ngắn, giàu từ khóa, giống cụm từ trong văn bản pháp luật.

Trả về đúng JSON:
{
  "matched_topic_title_en": "...",
  "matched_topic_ids": ["..."],
  "tone_guidance": "...",
  "requery_reason": "...",
  "search_queries": ["...", "..."]
}
"""


class RagRequeryResult(TypedDict):
    search_queries: list[str]
    matched_topic_title_en: str
    matched_topic_ids: list[str]
    tone_guidance: str
    requery_reason: str


def _get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider(llm_config)
    return _llm


def _format_chat_history(chat_history: list[dict[str, Any]] | None, limit: int = 8) -> str:
    if not chat_history:
        return ""
    lines: list[str] = []
    for item in chat_history[-limit:]:
        role = str(item.get("role") or "user").strip()
        content = str(item.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines).strip()


def _load_rag_ontology_catalog() -> list[dict[str, Any]]:
    topics_by_en = LegalTopicService.load_catalog_grouped_by_title_en()
    subjects_by_topic = LegalSubjectService.load_subjects_grouped_by_topic_id()
    catalog: list[dict[str, Any]] = []
    for title_en, topic in topics_by_en.items():
        topic_ids = topic.get("topic_ids") or []
        subjects: list[dict[str, str]] = []
        for tid in topic_ids:
            subjects.extend(subjects_by_topic.get(tid, []))
        seen_subjects: set[str] = set()
        unique_subjects: list[dict[str, str]] = []
        for sub in subjects:
            sid = sub.get("subject_id") or ""
            if sid and sid in seen_subjects:
                continue
            if sid:
                seen_subjects.add(sid)
            unique_subjects.append(sub)
        catalog.append(
            {
                "topic_title_en": title_en,
                "topic_title_vi": topic.get("topic_title_vi") or "",
                "topic_notes": topic.get("topic_notes") or [],
                "topic_ids": topic_ids,
                "subjects": unique_subjects[:40],
            }
        )
    return catalog


def _format_ontology_catalog_for_llm(catalog: list[dict[str, Any]], max_topics: int = 80) -> str:
    lines: list[str] = []
    for item in catalog[:max_topics]:
        notes = "; ".join(item.get("topic_notes") or []) or "(không có topic_note)"
        subject_titles = [
            s.get("subject_title", "")
            for s in (item.get("subjects") or [])
            if s.get("subject_title")
        ]
        subjects_preview = ", ".join(subject_titles[:12])
        if len(subject_titles) > 12:
            subjects_preview += f", ... (+{len(subject_titles) - 12})"
        lines.append(
            f"- topic_title_en: {item.get('topic_title_en')}\n"
            f"  topic_title_vi: {item.get('topic_title_vi')}\n"
            f"  topic_ids: {', '.join(item.get('topic_ids') or [])}\n"
            f"  topic_note: {notes}\n"
            f"  subject_titles: {subjects_preview or '(không có)'}"
        )
    return "\n\n".join(lines)


def understand_user_true_intent(
    chat_history: list[dict[str, Any]] | None,
    user_query: str,
) -> tuple[str, str]:
    """Suy luận yêu cầu thực sự của user từ hội thoại dài (không phải rewrite cho RAG)."""
    query = (user_query or "").strip()
    if not query:
        return "", "empty user query"

    history_text = _format_chat_history(chat_history)
    user_content = (
        f"Lịch sử chat:\n{history_text or '(không có)'}\n\n"
        f"Tin nhắn hiện tại của user:\n{query}\n"
    )
    raw = _get_llm().chat_text(
        [{"role": "user", "content": user_content}],
        system_prompt=_USER_INTENT_SYSTEM_PROMPT,
        temperature=0.0,
        max_tokens=280,
    )
    if not raw or not str(raw).strip():
        return query, "llm returned empty response"

    cleaned = _JSON_FENCE_RE.sub("", str(raw).strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("understand_user_true_intent: invalid json from llm: {}", cleaned)
        return query, "invalid llm json"

    if not isinstance(data, dict):
        return query, "llm response is not object"
    clarified = str(data.get("clarified_request") or "").strip() or query
    reason = str(data.get("intent_reason") or "").strip() or "intent resolved"
    return clarified, reason


def _fallback_rag_requery(clarified_query: str, reason: str) -> RagRequeryResult:
    return {
        "search_queries": [clarified_query],
        "matched_topic_title_en": "",
        "matched_topic_ids": [],
        "tone_guidance": "",
        "requery_reason": reason,
    }


def requery_for_rag(clarified_query: str) -> RagRequeryResult:
    """Sinh danh sách câu search RAG từ yêu cầu đã clarify + ontology legal_topics/legal_subjects."""
    query = (clarified_query or "").strip()
    logger.warning("requery_for_rag: called query_len={}", len(query))
    if not query:
        return _fallback_rag_requery("", "empty clarified query")

    try:
        catalog = _load_rag_ontology_catalog()
    except Exception as e:
        logger.error("failed to load ontology catalog: {}", e)
        return _fallback_rag_requery(query, "ontology catalog load failed")

    subject_count = sum(len(item.get("subjects") or []) for item in catalog)
    logger.info(
        "ontology loaded: topics={} subjects={}",
        len(catalog),
        subject_count,
    )
    if _RAG_REQUERY_DEBUG:
        for item in catalog[:5]:
            logger.info(
                "sample topic: en={!r} ids={} notes={} subjects={}",
                item.get("topic_title_en"),
                item.get("topic_ids"),
                len(item.get("topic_notes") or []),
                len(item.get("subjects") or []),
            )

    if not catalog:
        return _fallback_rag_requery(query, "empty ontology catalog")

    catalog_text = _format_ontology_catalog_for_llm(catalog)
    user_content = (
        f"Yêu cầu đã làm rõ của user:\n{query}\n\n"
        f"Catalog chủ đề trong hệ thống RAG:\n{catalog_text}\n"
    )
    logger.info(
        "llm input: clarified_len={} catalog_chars={}",
        len(query),
        len(catalog_text),
    )
    if _RAG_REQUERY_DEBUG:
        logger.warning("user_content (debug):\n{}", user_content)
    raw = _get_llm().chat_text(
        [{"role": "user", "content": user_content}],
        system_prompt=_RAG_REQUERY_SYSTEM_PROMPT,
        temperature=0.0,
        max_tokens=720,
    )
    logger.info("llm raw_len={}", len(str(raw or "")))
    if _RAG_REQUERY_DEBUG:
        logger.warning("llm raw (debug):\n{}", raw)
    if not raw or not str(raw).strip():
        return _fallback_rag_requery(query, "llm returned empty response")

    cleaned = _JSON_FENCE_RE.sub("", str(raw).strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("requery_for_rag: invalid json from llm: {}", cleaned)
        return _fallback_rag_requery(query, "invalid llm json")

    if not isinstance(data, dict):
        return _fallback_rag_requery(query, "llm response is not object")

    raw_queries = data.get("search_queries")
    search_queries: list[str] = []
    if isinstance(raw_queries, list):
        for item in raw_queries:
            text = str(item or "").strip()
            if text and text not in search_queries:
                search_queries.append(text)
    if not search_queries:
        search_queries = [query]

    matched_topic_ids: list[str] = []
    raw_topic_ids = data.get("matched_topic_ids")
    if isinstance(raw_topic_ids, list):
        for item in raw_topic_ids:
            tid = str(item or "").strip()
            if tid and tid not in matched_topic_ids:
                matched_topic_ids.append(tid)

    return {
        "search_queries": search_queries,
        "matched_topic_title_en": str(data.get("matched_topic_title_en") or "").strip(),
        "matched_topic_ids": matched_topic_ids,
        "tone_guidance": str(data.get("tone_guidance") or "").strip(),
        "requery_reason": str(data.get("requery_reason") or "").strip() or "rag requery planned",
    }
