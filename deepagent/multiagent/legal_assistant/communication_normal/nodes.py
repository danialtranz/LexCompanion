from __future__ import annotations

import json
import re
from typing import Any

from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState

logger = setup_logging()

_llm: LLMProvider | None = None
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

_COMMUNICATION_SYSTEM_PROMPT = """Bạn là trợ lý chatbot tư vấn pháp luật Việt Nam, thân thiện và tự nhiên.

Người dùng đang trò chuyện thông thường: chào hỏi, cảm ơn, xã giao, hỏi bạn là ai, hoặc nội dung không cần tra cứu văn bản pháp luật.

Bạn PHẢI trả về đúng một JSON hợp lệ (không markdown):
{
  "answer": "..."
}

Quy tắc:
- Trả lời ngắn gọn, thân thiện, tiếng Việt.
- Không gọi tra cứu luật, không trích dẫn điều khoản, không bịa văn bản.
- Nhẹ nhàng mời người dùng đặt câu hỏi pháp luật cụ thể nếu họ cần hỗ trợ chuyên môn.
"""


def _get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider(llm_config)
    return _llm


def _parse_answer(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    text = _JSON_FENCE_RE.sub("", str(raw).strip()).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            answer = data.get("answer")
            if answer is not None and str(answer).strip():
                return str(answer).strip()
    except json.JSONDecodeError:
        pass
    return text


def _format_history(chat_history: list[dict[str, Any]] | None, limit: int = 6) -> str:
    if not chat_history:
        return ""
    lines: list[str] = []
    for item in chat_history[-limit:]:
        role = str(item.get("role") or "user")
        content = str(item.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def run_communication_response(state: LegalAssistantState) -> LegalAssistantState:
    query = (state.get("user_query") or "").strip()
    history = _format_history(state.get("chat_history"))
    parts = [f"Tin nhắn người dùng:\n{query}"]
    if history:
        parts.insert(0, f"Lịch sử gần đây:\n{history}\n")

    raw = _get_llm().chat_text(
        [{"role": "user", "content": "\n".join(parts)}],
        system_prompt=_COMMUNICATION_SYSTEM_PROMPT,
        max_tokens=400,
        temperature=0.4,
    )
    answer = _parse_answer(raw) or (
        "Xin chào! Mình là trợ lý pháp luật. "
        "Bạn có thể hỏi mình về quy định, thủ tục hoặc tình huống pháp lý cụ thể nhé."
    )

    next_state = dict(state)
    next_state["output"] = {
        "query": query,
        "answer": answer,
        "reference": [],
        "answer_mode": "communication_normal",
        "intent": "communication_normal",
    }
    next_state["response"] = answer
    next_state["citations"] = []
    return next_state
