from __future__ import annotations

import json
import re
from typing import Any

from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging
from deepagent.core.query_rewriting.rewrite import rewrite_query
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.tools.legal_retrieval import run_legal_retrieval
from deepagent.multiagent.legal_assistant.tools.web_search import run_web_search

logger = setup_logging()

_llm: LLMProvider | None = None
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_INSUFFICIENT_HINT_RE = re.compile(
    r"không đủ căn cứ|chưa đủ căn cứ|không đủ thông tin|chưa đủ thông tin",
    re.IGNORECASE,
)

_REASON_IF_ENOUGH_PROMPT = """Bạn là bộ đánh giá ngữ cảnh cho câu hỏi pháp lý.
Input gồm:
- user_query
- rewritten_query
- answer
- references

Trả về JSON:
{
  "is_context_sufficient": true,
  "insufficiency_reason": "...",
  "query_expansion_hint": "..."
}

Quy tắc:
- sufficient=true khi answer trả lời trực tiếp câu hỏi và có căn cứ hợp lý.
- Nếu chưa đủ, nêu ngắn gọn thiếu gì và gợi ý mở rộng query để RAG vòng sau.
"""

_EXPAND_QUERY_PROMPT = """Bạn là trợ lý mở rộng truy vấn cho RAG pháp lý.
Từ rewritten_query hiện tại + insufficiency_reason, tạo truy vấn tốt hơn cho vòng kế.

Trả về JSON:
{
  "expanded_query": "...",
  "why": "..."
}
"""


def _get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider(llm_config)
    return _llm


def _parse_json_dict(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return {}
    cleaned = _JSON_FENCE_RE.sub("", str(raw).strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("information.nodes invalid json: {}", cleaned)
        return {}
    return data if isinstance(data, dict) else {}


def rewrite_query_from_history(state: LegalAssistantState) -> LegalAssistantState:
    rewritten, reason = rewrite_query(
        state.get("chat_history") or [],
        state.get("user_query", ""),
    )
    next_state = dict(state)
    next_state["rewritten_query"] = rewritten
    next_state["query_expansion_hint"] = reason
    next_state["rag_iteration"] = 0
    next_state["retrieval_attempts"] = []
    next_state["web_search_used"] = False
    next_state["web_results"] = []
    return next_state


def rag_retrieve(state: LegalAssistantState) -> LegalAssistantState:
    iteration = int(state.get("rag_iteration", 0)) + 1
    query = state.get("rewritten_query") or state.get("user_query", "")
    payload = run_legal_retrieval(
        query=query,
        session_id=state.get("session_id"),
        user_id=state.get("user_id"),
        candidate_size=state.get("candidate_size", 100),
        similarity_threshold=state.get("similarity_threshold", 0.5),
        final_size=state.get("final_size", 5),
        keyword_weight=state.get("keyword_weight", 0.3),
        field_weights=state.get("field_weights"),
        topic_ids=state.get("topic_ids"),
        subject_ids=state.get("subject_ids"),
        doc_ids=state.get("doc_ids"),
        reranker=state.get("reranker"),
    )
    attempts = list(state.get("retrieval_attempts") or [])
    attempts.append(
        {
            "iteration": iteration,
            "query": query,
            "answer": payload.get("answer"),
            "reference_count": len(payload.get("reference") or []),
        }
    )
    next_state = dict(state)
    next_state["rag_iteration"] = iteration
    next_state["retrieval_attempts"] = attempts
    next_state["retrieval_payload"] = payload
    next_state["response"] = payload.get("answer")
    next_state["citations"] = payload.get("reference") or []
    return next_state


def reason_if_enough(state: LegalAssistantState) -> LegalAssistantState:
    payload = state.get("retrieval_payload") or {}
    answer = str(payload.get("answer") or "").strip()
    references = payload.get("reference") or []

    heuristic_insufficient = (not answer) or (
        bool(_INSUFFICIENT_HINT_RE.search(answer)) and len(references) == 0
    )
    if heuristic_insufficient:
        next_state = dict(state)
        next_state["is_context_sufficient"] = False
        next_state["insufficiency_reason"] = (
            "Answer chưa đủ căn cứ hoặc không trả lời trực tiếp câu hỏi."
        )
        next_state["query_expansion_hint"] = (
            "Bổ sung chủ thể, hành vi, thời điểm, điều luật/thủ tục liên quan."
        )
        return next_state

    judge_input = {
        "user_query": state.get("user_query", ""),
        "rewritten_query": state.get("rewritten_query", ""),
        "answer": answer,
        "references": references,
    }
    raw = _get_llm().chat_text(
        [{"role": "user", "content": json.dumps(judge_input, ensure_ascii=False)}],
        system_prompt=_REASON_IF_ENOUGH_PROMPT,
        temperature=0.0,
        max_tokens=220,
    )
    data = _parse_json_dict(raw)
    is_sufficient = bool(data.get("is_context_sufficient", True))
    insuff_reason = str(data.get("insufficiency_reason") or "").strip()
    expand_hint = str(data.get("query_expansion_hint") or "").strip()

    next_state = dict(state)
    next_state["is_context_sufficient"] = is_sufficient
    next_state["insufficiency_reason"] = insuff_reason
    next_state["query_expansion_hint"] = expand_hint
    return next_state


def expand_query_for_next_rag(state: LegalAssistantState) -> LegalAssistantState:
    current_query = state.get("rewritten_query") or state.get("user_query", "")
    insuff_reason = state.get("insufficiency_reason", "")
    hint = state.get("query_expansion_hint", "")
    raw = _get_llm().chat_text(
        [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "current_query": current_query,
                        "insufficiency_reason": insuff_reason,
                        "query_expansion_hint": hint,
                    },
                    ensure_ascii=False,
                ),
            }
        ],
        system_prompt=_EXPAND_QUERY_PROMPT,
        temperature=0.0,
        max_tokens=180,
    )
    data = _parse_json_dict(raw)
    expanded_query = str(data.get("expanded_query") or "").strip() or current_query
    next_state = dict(state)
    next_state["rewritten_query"] = expanded_query
    return next_state


def web_search_tavily(state: LegalAssistantState) -> LegalAssistantState:
    query = state.get("rewritten_query") or state.get("user_query", "")
    web_payload = run_web_search(query=query, limit=5)
    results = web_payload.get("results") or []
    next_state = dict(state)
    next_state["web_search_used"] = True
    next_state["web_results"] = results
    return next_state


def synthesize_with_web(state: LegalAssistantState) -> LegalAssistantState:
    retrieval_payload = state.get("retrieval_payload") or {}
    base_answer = str(retrieval_payload.get("answer") or "").strip()
    web_results = state.get("web_results") or []
    note = (
        "\n\n[Web fallback] Đã dùng tìm kiếm ngoài do RAG nội bộ chưa đủ sau 2 vòng."
        if state.get("web_search_used")
        else ""
    )
    answer = base_answer + note if base_answer else note.strip()
    next_state = dict(state)
    next_state["output"] = {
        **retrieval_payload,
        "answer": answer or retrieval_payload.get("answer"),
        "web_search_used": bool(state.get("web_search_used")),
        "web_results": web_results,
        "rag_iteration": state.get("rag_iteration", 0),
        "retrieval_attempts": state.get("retrieval_attempts") or [],
    }
    next_state["response"] = next_state["output"].get("answer")
    next_state["citations"] = retrieval_payload.get("reference") or []
    return next_state


def compose_final_answer(state: LegalAssistantState) -> LegalAssistantState:
    payload = state.get("retrieval_payload") or {}
    next_state = dict(state)
    next_state["output"] = {
        **payload,
        "web_search_used": bool(state.get("web_search_used")),
        "rag_iteration": state.get("rag_iteration", 0),
        "retrieval_attempts": state.get("retrieval_attempts") or [],
    }
    next_state["response"] = next_state["output"].get("answer")
    next_state["citations"] = next_state["output"].get("reference") or []
    return next_state


def route_after_reason(state: LegalAssistantState) -> str:
    if state.get("is_context_sufficient"):
        return "enough"
    if int(state.get("rag_iteration", 0)) < 2:
        return "retry_rag"
    return "fallback_web"
