from __future__ import annotations

import json
import re
from typing import Any

from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging
from deepagent.core.hitl import (
    HitlAssessment,
    assess_rag_for_hitl,
    assess_web_for_hitl,
    compose_clarification_answer,
)
from deepagent.core.query_rewriting.rewrite import requery_for_rag
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.tools.legal_retrieval import (
    run_legal_retrieval,
    run_legal_retrieval_multi,
)
from deepagent.multiagent.legal_assistant.tools.web_search import run_web_search

logger = setup_logging()

_llm: LLMProvider | None = None
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_INSUFFICIENT_HINT_RE = re.compile(
    r"không đủ căn cứ|chưa đủ căn cứ|không đủ thông tin|chưa đủ thông tin",
    re.IGNORECASE,
)

_WEB_SYNTH_SYSTEM_PROMPT = """Bạn là trợ lý tư vấn pháp luật Việt Nam.

Nhiệm vụ: trả lời câu hỏi dựa trên các đoạn tài liệu web được đánh số [1], [2], ... trong tin nhắn người dùng.
Có thể tham khảo thêm phần tài liệu pháp luật nội bộ (nếu được cung cấp), nhưng ưu tiên thông tin web khi phần nội bộ không đủ.

Bạn PHẢI trả về đúng một JSON hợp lệ (không markdown, không giải thích thêm), schema:
{
  "answer": "...",
  "cited_indexes": [1, 2]
}

Quy tắc:
- Trong "answer": tiếng Việt, súc tích; mọi luận điểm lấy từ tài liệu được cung cấp phải có trích dẫn nội tuyến [1], [2] ngay sau câu/đoạn tương ứng.
- "cited_indexes": danh sách số nguyên (1-based) trùng với các [n] đã dùng, không trùng lặp, sắp xếp tăng dần.
- Chỉ dùng chỉ số [n] có trong tài liệu được cung cấp; không bịa điều luật hay mức phạt.
- Ghi chú ngắn nguồn web mang tính tham khảo, người dùng nên đối chiếu văn bản pháp luật chính thức.
"""

_WEB_SYNTH_NO_SOURCES_PROMPT = """Bạn là trợ lý tư vấn pháp luật Việt Nam.

Tình huống: hệ thống đã tìm RAG nội bộ và tìm kiếm web nhưng KHÔNG có đoạn tài liệu nào đủ tin cậy để trích dẫn.
Không có danh sách [1], [2], ... được cung cấp cho bạn.

Bạn PHẢI trả về đúng một JSON hợp lệ (không markdown, không giải thích thêm), schema:
{
  "answer": "...",
  "cited_indexes": []
}

Quy tắc:
- Trả lời thoải mái dựa trên kiến thức pháp luật Việt Nam chung của bạn; giải thích rõ ràng, hữu ích.
- "cited_indexes" LUÔN là [] — không dùng [1], [2] trong answer vì không có nguồn được cung cấp.
- Không bịa trích dẫn, không giả vờ trích từ văn bản/website cụ thể.
- Tránh khẳng định chắc chắn số tiền phạt, điều khoản như thể đã có văn bản chính thức; dùng ngôn ngữ thận trọng (thường, theo quy định chung, cần đối chiếu...).
- Mở đầu hoặc kết thúc answer bằng một câu ngắn: thông tin mang tính tham khảo, nên đối chiếu văn bản pháp luật hiện hành.
"""

_UNCITED_FALLBACK_DISCLAIMER = (
    "**Lưu ý:** Câu trả lời dưới đây không trích dẫn từ corpus pháp luật nội bộ, "
    "không trích dẫn từ kết quả tìm kiếm web, và không gắn với bất kỳ nguồn tài liệu nào "
    "trong hệ thống. Đây là tư vấn tham khảo chung; bạn cần đối chiếu văn bản pháp luật hiện hành."
)

_UNCITED_FALLBACK_PROMPT = """Bạn là trợ lý tư vấn pháp luật Việt Nam.

Hệ thống đã thử RAG nội bộ và/hoặc tìm web nhưng KHÔNG đủ tin cậy để trích dẫn nguồn.
Bạn phải trả lời dựa trên hiểu biết pháp luật Việt Nam chung.

Bạn PHẢI trả về JSON:
{
  "answer": "..."
}

Quy tắc:
- Tiếng Việt, hữu ích, thận trọng; KHÔNG dùng [1], [2] hoặc giả vờ trích dẫn.
- Không nói "theo điều X" như thể đã có văn bản trong hệ thống.
- Có thể tóm tắt hướng xử lý chung nếu thiếu dữ kiện cá nhân.
"""


def _get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider(llm_config)
    return _llm


def _parse_llm_answer_with_citations(raw: str | None) -> tuple[str | None, list[int]]:
    if not raw or not str(raw).strip():
        return None, []
    text = _JSON_FENCE_RE.sub("", str(raw).strip()).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            answer = data.get("answer")
            indexes_raw = data.get("cited_indexes") or []
            indexes: list[int] = []
            for item in indexes_raw:
                try:
                    n = int(item)
                    if n > 0:
                        indexes.append(n)
                except (TypeError, ValueError):
                    continue
            indexes = sorted(set(indexes))
            if answer is not None and str(answer).strip():
                return str(answer).strip(), indexes
    except json.JSONDecodeError:
        logger.warning("information.nodes: answer json parse failed")
    return text, sorted({int(m) for m in re.findall(r"\[(\d+)\]", text)})


def _web_results_to_context(web_results: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for index, item in enumerate(web_results, start=1):
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        header = f"[{index}]"
        if title:
            header += f" {title}"
        if url:
            header += f" ({url})"
        parts.append(f"{header}\n{content}")
    return "\n\n".join(parts).strip()


def _build_web_references(
    web_results: list[dict[str, Any]],
    cited_indexes: list[int],
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    max_index = len(web_results)
    for index in cited_indexes:
        if index < 1 or index > max_index:
            continue
        item = web_results[index - 1]
        title = str(item.get("title") or "Nguồn web").strip()
        url = str(item.get("url") or "").strip()
        ieee = f"[{index}] {title}"
        if url:
            ieee += f", {url}"
        references.append(
            {
                "index": index,
                "ieee": ieee,
                "source_type": "web",
                "title": title,
                "url": url,
                "content_text": item.get("content"),
                "score": item.get("score"),
            }
        )
    return references


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


def plan_rag_search_queries(state: LegalAssistantState) -> LegalAssistantState:
    clarified = (state.get("resolved_user_request") or state.get("user_query") or "").strip()
    logger.warning(
        "plan_rag_search_queries: bắt đầu requery (rag_iteration={}) query={!r}",
        state.get("rag_iteration", 0),
        clarified[:200],
    )
    requery = requery_for_rag(clarified)
    next_state = dict(state)
    next_state["rag_search_queries"] = requery.get("search_queries") or [clarified]
    next_state["rag_matched_topic_ids"] = requery.get("matched_topic_ids") or []
    next_state["rag_requery_reason"] = requery.get("requery_reason") or ""
    topic_ids = list(state.get("topic_ids") or [])
    for tid in next_state["rag_matched_topic_ids"]:
        if tid and tid not in topic_ids:
            topic_ids.append(tid)
    if topic_ids:
        next_state["topic_ids"] = topic_ids
    logger.info(
        "plan_rag_search_queries: queries={} topic_ids={} reason={}",
        len(next_state["rag_search_queries"]),
        next_state["rag_matched_topic_ids"],
        next_state["rag_requery_reason"],
    )
    ## in ra detail các query được sinh ra
    logger.info("plan_rag_search_queries: queries={}", next_state["rag_search_queries"])
    return next_state


def rag_retrieve(state: LegalAssistantState) -> LegalAssistantState:
    iteration = int(state.get("rag_iteration", 0)) + 1
    primary_query = state.get("resolved_user_request") or state.get("user_query", "")
    search_queries = list(state.get("rag_search_queries") or [])
    if not search_queries:
        search_queries = [primary_query]
    topic_ids = state.get("topic_ids")
    subject_ids = state.get("subject_ids")
    retrieval_kwargs = {
        "session_id": state.get("session_id"),
        "user_id": state.get("user_id"),
        "candidate_size": state.get("candidate_size", 100),
        "similarity_threshold": state.get("similarity_threshold", 0.5),
        "final_size": state.get("final_size", 5),
        "keyword_weight": state.get("keyword_weight", 0.3),
        "field_weights": state.get("field_weights"),
        "topic_ids": topic_ids,
        "subject_ids": subject_ids,
        "doc_ids": state.get("doc_ids"),
        "reranker": state.get("reranker"),
    }
    if len(search_queries) > 1:
        payload = run_legal_retrieval_multi(
            queries=search_queries,
            primary_query=primary_query,
            **retrieval_kwargs,
        )
    else:
        payload = run_legal_retrieval(query=search_queries[0], **retrieval_kwargs)
    attempts = list(state.get("retrieval_attempts") or [])
    attempts.append(
        {
            "iteration": iteration,
            "query": primary_query,
            "search_queries": search_queries,
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
    next_state["reason_phase"] = "rag"
    return next_state


def reason_if_enough(state: LegalAssistantState) -> LegalAssistantState:
    phase = state.get("reason_phase") or "rag"
    payload = state.get("retrieval_payload") or {}
    answer = str(payload.get("answer") or "").strip()
    references = payload.get("reference") or []

    heuristic_insufficient = (not answer) or (
        bool(_INSUFFICIENT_HINT_RE.search(answer)) and len(references) == 0
    )
    if heuristic_insufficient and phase == "rag":
        next_state = dict(state)
        next_state["is_context_sufficient"] = False
        next_state["needs_user_clarification"] = False
        next_state["missing_facts"] = []
        next_state["clarification_questions"] = []
        next_state["insufficiency_reason"] = (
            "Answer chưa đủ căn cứ hoặc không trả lời trực tiếp câu hỏi."
        )
        next_state["hitl_assessment_reason"] = "heuristic insufficient"
        return next_state

    if phase == "web":
        assessment = assess_web_for_hitl(
            user_query=state.get("user_query", ""),
            resolved_user_request=state.get("resolved_user_request", ""),
            synthesized_answer=answer,
            references=references,
            web_results=state.get("web_results"),
            chat_history=state.get("chat_history"),
        )
    else:
        assessment = assess_rag_for_hitl(
            user_query=state.get("user_query", ""),
            resolved_user_request=state.get("resolved_user_request", ""),
            rag_answer=answer,
            references=references,
            chat_history=state.get("chat_history"),
        )

    next_state = dict(state)
    next_state["is_context_sufficient"] = assessment["is_context_sufficient"]
    next_state["needs_user_clarification"] = assessment["needs_user_clarification"]
    next_state["missing_facts"] = assessment["missing_facts"]
    next_state["clarification_questions"] = assessment["clarification_questions"]
    next_state["partial_answer_preface"] = assessment["partial_answer_preface"]
    next_state["insufficiency_reason"] = assessment["insufficiency_reason"]
    next_state["hitl_assessment_reason"] = assessment["assessment_reason"]
    logger.info(
        "reason_if_enough: phase={} sufficient={} needs_clarification={} hitl_used={}",
        phase,
        next_state["is_context_sufficient"],
        next_state["needs_user_clarification"],
        bool(state.get("hitl_used")),
    )
    return next_state


def compose_user_clarification(state: LegalAssistantState) -> LegalAssistantState:
    """Trả lời một phần + hỏi user bổ sung hoàn cảnh để áp dụng luật đúng case."""
    payload = state.get("retrieval_payload") or {}
    hitl: HitlAssessment = {
        "is_context_sufficient": bool(state.get("is_context_sufficient")),
        "needs_user_clarification": True,
        "missing_facts": list(state.get("missing_facts") or []),
        "clarification_questions": list(state.get("clarification_questions") or []),
        "partial_answer_preface": str(state.get("partial_answer_preface") or "").strip(),
        "insufficiency_reason": str(state.get("insufficiency_reason") or ""),
        "assessment_reason": str(state.get("hitl_assessment_reason") or ""),
    }
    clarification_answer = compose_clarification_answer(hitl)

    next_state = dict(state)
    next_state["output"] = {
        **payload,
        "query": state.get("resolved_user_request") or state.get("user_query", ""),
        "answer": clarification_answer,
        "reference": payload.get("reference") or [],
        "answer_mode": "needs_user_clarification",
        "hitl": {
            "status": "needs_clarification",
            "missing_facts": state.get("missing_facts") or [],
            "clarification_questions": state.get("clarification_questions") or [],
            "assessment_reason": state.get("hitl_assessment_reason") or "",
        },
        "web_search_used": bool(state.get("web_search_used")),
        "rag_iteration": state.get("rag_iteration", 0),
        "retrieval_attempts": state.get("retrieval_attempts") or [],
    }
    next_state["response"] = clarification_answer
    next_state["citations"] = next_state["output"].get("reference") or []
    next_state["hitl_used"] = True
    return next_state


def compose_uncited_fallback(state: LegalAssistantState) -> LegalAssistantState:
    """Trả lời tham khảo chung, không trích dẫn bất kỳ nguồn nào."""
    user_query = (
        state.get("resolved_user_request") or state.get("user_query") or ""
    ).strip()
    draft = str((state.get("retrieval_payload") or {}).get("answer") or "").strip()
    draft = re.sub(r"\[\d+\]", "", draft)
    draft = re.sub(r"\s{2,}", " ", draft).strip()

    parts = [f"Câu hỏi:\n{user_query}\n"]
    if draft:
        parts.append(
            "Bản tổng hợp trước đó (không dùng làm trích dẫn, chỉ tham khảo nội dung):\n"
            f"{draft}"
        )
    raw = _get_llm().chat_text(
        [{"role": "user", "content": "\n\n".join(parts)}],
        system_prompt=_UNCITED_FALLBACK_PROMPT,
        max_tokens=2000,
        temperature=0.3,
    )
    answer, _ = _parse_llm_answer_with_citations(raw)
    if not answer:
        answer = (
            "Hiện hệ thống chưa đủ căn cứ từ tài liệu pháp luật nội bộ hoặc web "
            "để trả lời chắc chắn. Bạn nên mô tả thêm hoàn cảnh cụ thể hoặc đối chiếu "
            "văn bản pháp luật hiện hành với cơ quan có thẩm quyền."
        )
    else:
        answer = re.sub(r"\[\d+\]", "", answer).strip()

    full_answer = f"{_UNCITED_FALLBACK_DISCLAIMER}\n\n{answer}"

    next_state = dict(state)
    next_state["output"] = {
        "query": user_query,
        "answer": full_answer,
        "reference": [],
        "answer_mode": "uncited_fallback",
        "web_search_used": bool(state.get("web_search_used")),
        "web_results": state.get("web_results") or [],
        "rag_iteration": state.get("rag_iteration", 0),
        "retrieval_attempts": state.get("retrieval_attempts") or [],
        "hitl": {
            "status": "uncited_fallback",
            "assessment_reason": state.get("hitl_assessment_reason") or "",
        },
    }
    next_state["response"] = full_answer
    next_state["citations"] = []
    return next_state


def web_search_tavily(state: LegalAssistantState) -> LegalAssistantState:
    query = state.get("resolved_user_request") or state.get("user_query", "")
    web_payload = run_web_search(query=query, limit=5)
    results = web_payload.get("results") or []
    next_state = dict(state)
    next_state["web_search_used"] = True
    next_state["web_results"] = results
    return next_state


def synthesize_with_web(state: LegalAssistantState) -> LegalAssistantState:
    retrieval_payload = state.get("retrieval_payload") or {}
    web_results = state.get("web_results") or []
    user_query = (
        state.get("resolved_user_request") or state.get("user_query") or ""
    ).strip()
    web_context = _web_results_to_context(web_results)

    answer: str | None = None
    cited_indexes: list[int] = []
    answer_mode = "grounded_web"
    rag_refs = list(retrieval_payload.get("reference") or [])

    if web_context:
        parts = [f"Câu hỏi:\n{user_query}\n"]
        rag_answer = str(retrieval_payload.get("answer") or "").strip()
        if rag_answer:
            parts.append(
                "Kết quả RAG nội bộ (có thể không đủ, chỉ tham khảo):\n"
                f"{rag_answer}"
            )
        parts.append(
            "Tài liệu tham chiếu từ tìm kiếm web (trích dẫn theo số [n]):\n"
            f"{web_context}"
        )
        raw = _get_llm().chat_text(
            [{"role": "user", "content": "\n\n".join(parts)}],
            system_prompt=_WEB_SYNTH_SYSTEM_PROMPT,
            max_tokens=2000,
            temperature=0.2,
        )
        answer, cited_indexes = _parse_llm_answer_with_citations(raw)
        if answer:
            from_answer = {int(m) for m in re.findall(r"\[(\d+)\]", answer)}
            cited_indexes = sorted(set(cited_indexes) | from_answer)
    else:
        # Tavily/RAG không trả chunk đạt ngưỡng — trả lời theo kiến thức chung, không trích dẫn giả.
        answer_mode = "general_knowledge"
        parts = [
            f"Câu hỏi:\n{user_query}\n",
            (
                "Hệ thống đã tìm kiếm corpus pháp luật nội bộ và web "
                "nhưng không thu được đoạn tài liệu nào đủ tin cậy để trích dẫn. "
                "Hãy trả lời dựa trên hiểu biết pháp luật Việt Nam chung của bạn."
            ),
        ]
        raw = _get_llm().chat_text(
            [{"role": "user", "content": "\n\n".join(parts)}],
            system_prompt=_WEB_SYNTH_NO_SOURCES_PROMPT,
            max_tokens=2000,
            temperature=0.3,
        )
        answer, _ = _parse_llm_answer_with_citations(raw)
        cited_indexes = []
        if answer:
            answer = re.sub(r"\[\d+\]", "", answer)
            answer = re.sub(r"\s{2,}", " ", answer).strip()

    if not answer:
        if web_results:
            first = web_results[0]
            snippet = str(first.get("content") or "")[:500].strip()
            answer = (
                "Không tổng hợp được câu trả lời đầy đủ từ LLM. "
                f"Tham khảo nguồn web: {first.get('title') or first.get('url')}. "
                f"{snippet}"
            )
            cited_indexes = [1]
            answer_mode = "grounded_web"
        else:
            answer = (
                "Thông tin mang tính tham khảo. "
                "Hệ thống chưa truy xuất được tài liệu pháp luật hoặc nguồn web đủ tin cậy; "
                "bạn nên đối chiếu văn bản pháp luật hiện hành trước khi áp dụng."
            )
            cited_indexes = []
            answer_mode = "general_knowledge"

    web_refs = _build_web_references(web_results, cited_indexes)
    merged_refs = list(rag_refs) + web_refs

    next_state = dict(state)
    next_state["retrieval_payload"] = {
        "query": user_query or retrieval_payload.get("query"),
        "answer": answer,
        "reference": merged_refs,
        "answer_mode": answer_mode,
    }
    next_state["reason_phase"] = "web"
    return next_state


def compose_final_answer(state: LegalAssistantState) -> LegalAssistantState:
    payload = state.get("retrieval_payload") or {}
    next_state = dict(state)
    next_state["output"] = {
        **payload,
        "web_search_used": bool(state.get("web_search_used")),
        "web_results": state.get("web_results") or [],
        "rag_iteration": state.get("rag_iteration", 0),
        "retrieval_attempts": state.get("retrieval_attempts") or [],
    }
    next_state["response"] = next_state["output"].get("answer")
    next_state["citations"] = next_state["output"].get("reference") or []
    return next_state


def route_after_reason(state: LegalAssistantState) -> str:
    phase = state.get("reason_phase") or "rag"
    iteration = int(state.get("rag_iteration", 0))
    hitl_used = bool(state.get("hitl_used"))

    if phase == "web":
        if (
            state.get("needs_user_clarification")
            and state.get("is_context_sufficient")
            and not hitl_used
        ):
            logger.info("route_after_reason: ask_user (web)")
            return "ask_user"
        if state.get("is_context_sufficient") and not state.get(
            "needs_user_clarification"
        ):
            logger.info("route_after_reason: enough (web)")
            return "enough"
        logger.info(
            "route_after_reason: uncited_fallback (web) hitl_used={}",
            hitl_used,
        )
        return "uncited_fallback"

    if (
        state.get("needs_user_clarification")
        and state.get("is_context_sufficient")
        and not hitl_used
    ):
        logger.info("route_after_reason: ask_user (rag)")
        return "ask_user"
    if state.get("is_context_sufficient"):
        logger.info("route_after_reason: enough (rag)")
        return "enough"
    if iteration < 2:
        logger.info("route_after_reason: retry_rag (rag_iteration={})", iteration)
        return "retry_rag"
    logger.info("route_after_reason: fallback_web (rag_iteration={})", iteration)
    return "fallback_web"
