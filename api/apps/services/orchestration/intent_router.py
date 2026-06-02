from __future__ import annotations

import json
import re

from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging

from .schemas import RoutingDecision

logger = setup_logging()

_ROUTER_SYSTEM_PROMPT = """Bạn là bộ định tuyến intent cho chatbot pháp luật.

Phân loại câu hỏi người dùng vào ĐÚNG 1 intent:
- information: hỏi luật, hỏi quy định, hỏi điều khoản
- decision: hỏi nên làm gì, phải trả bao nhiêu, chọn phương án
- task_execution: yêu cầu tạo/sinh tài liệu, đơn từ, mẫu văn bản
- problem_solving: vụ việc cụ thể cần xử lý theo tình huống thực tế
- exploration: hỏi định hướng tối ưu, so sánh lựa chọn, chiến lược tốt nhất

Bạn PHẢI trả về đúng một JSON hợp lệ (không markdown, không giải thích):
{
  "intent": "information|decision|task_execution|problem_solving|exploration",
  "confidence": 0.0,
  "reason": "..."
}

Ràng buộc:
- confidence trong [0, 1]
- Nếu không chắc chắn, ưu tiên "information"
"""
_VALID_INTENTS = {
    "information",
    "decision",
    "task_execution",
    "problem_solving",
    "exploration",
}
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

_llm: LLMProvider | None = None


def _get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider(llm_config)
    return _llm


def _fallback_decision(reason: str) -> RoutingDecision:
    return RoutingDecision(
        intent="information",
        confidence=0.2,
        reason=reason,
        metadata={"router_version": "v1-llm", "fallback": True},
    )


def _parse_router_response(raw: str | None) -> RoutingDecision:
    if not raw or not str(raw).strip():
        return _fallback_decision("empty llm response")

    text = _JSON_FENCE_RE.sub("", str(raw).strip()).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("intent_router: invalid json from llm: {}", text)
        return _fallback_decision("invalid llm json")

    if not isinstance(data, dict):
        return _fallback_decision("llm response is not object")

    intent = str(data.get("intent") or "").strip()
    if intent not in _VALID_INTENTS:
        return _fallback_decision(f"invalid intent: {intent or 'empty'}")

    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    reason = str(data.get("reason") or "").strip() or "llm classified"
    return RoutingDecision(
        intent=intent,  # type: ignore[arg-type]
        confidence=confidence,
        reason=reason,
        metadata={"router_version": "v1-llm", "fallback": False},
    )


def route_intent(
    *,
    query: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> RoutingDecision:
    user_message = (
        f"query: {query}\n"
        f"session_id: {session_id or ''}\n"
        f"user_id: {user_id or ''}\n"
    )
    raw = _get_llm().chat_text(
        [{"role": "user", "content": user_message}],
        system_prompt=_ROUTER_SYSTEM_PROMPT,
        max_tokens=220,
        temperature=0.0,
    )
    decision = _parse_router_response(raw)
    logger.info(
        "intent_router: intent={} confidence={} reason={}",
        decision.intent,
        decision.confidence,
        decision.reason,
    )
    return decision
