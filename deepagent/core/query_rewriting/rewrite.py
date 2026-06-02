from __future__ import annotations

import json
import re
from typing import Any

from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging

logger = setup_logging()

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_llm: LLMProvider | None = None

_QUERY_REWRITE_SYSTEM_PROMPT = """Bạn là trợ lý viết lại truy vấn pháp lý.
Mục tiêu: kết hợp lịch sử chat + câu hỏi hiện tại thành một truy vấn độc lập, rõ nghĩa, đủ ngữ cảnh để truy xuất RAG.

Bạn PHẢI trả về đúng JSON:
{
  "rewritten_query": "...",
  "rewrite_reason": "..."
}

Quy tắc:
- Giữ nguyên ý định pháp lý ban đầu.
- Không thêm dữ kiện không có trong lịch sử chat.
- Nếu câu hỏi hiện tại đã rõ thì rewritten_query gần như giữ nguyên.
"""


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


def rewrite_query(
    chat_history: list[dict[str, Any]] | None,
    user_query: str,
) -> tuple[str, str]:
    query = (user_query or "").strip()
    if not query:
        return "", "empty user query"

    history_text = _format_chat_history(chat_history)
    user_content = (
        f"Lịch sử chat:\n{history_text or '(không có)'}\n\n"
        f"Câu hỏi hiện tại:\n{query}\n"
    )
    raw = _get_llm().chat_text(
        [{"role": "user", "content": user_content}],
        system_prompt=_QUERY_REWRITE_SYSTEM_PROMPT,
        temperature=0.0,
        max_tokens=220,
    )
    if not raw or not str(raw).strip():
        return query, "llm returned empty response"

    cleaned = _JSON_FENCE_RE.sub("", str(raw).strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("rewrite_query: invalid json from llm: {}", cleaned)
        return query, "invalid llm json"

    if not isinstance(data, dict):
        return query, "llm response is not object"
    rewritten = str(data.get("rewritten_query") or "").strip() or query
    reason = str(data.get("rewrite_reason") or "").strip() or "llm rewrite"
    return rewritten, reason
