"""Admin legal corpus retrieval: ES hybrid search → rerank → LLM answer."""

from __future__ import annotations

import json
import re
from typing import Any

from api.apps.services.chat_service import ChatSessionService
from api.utils.elastic_chunk_index import LexChunkSearch, hit_to_api_chunk
from api.utils.token_count import (
    RETRIEVAL_CONTEXT_MAX_TOKENS,
    count_tokens,
    trim_text_to_token_budget,
)
from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging
from deepagent.core.rerank.rerank import BgeM3Reranker, get_reranker, is_reranker_ready

logger = setup_logging()

_RETRIEVAL_SYSTEM_PROMPT = """Bạn là trợ lý tư vấn pháp luật Việt Nam.

Nhiệm vụ: trả lời câu hỏi CHỈ dựa trên các đoạn tài liệu được đánh số [1], [2], ... trong tin nhắn người dùng.

Bạn PHẢI trả về đúng một JSON hợp lệ (không markdown, không giải thích thêm), schema:
{
  "answer": "...",
  "cited_indexes": [1, 2]
}

Quy tắc:
- Trong "answer": tiếng Việt, súc tích; mọi luận điểm lấy từ tài liệu phải có trích dẫn nội tuyến kiểu IEEE dạng [1], [2] ngay sau câu/đoạn tương ứng.
- "cited_indexes": danh sách số nguyên (1-based) trùng với các [n] đã dùng trong answer, không trùng lặp, sắp xếp tăng dần.
- Chỉ dùng chỉ số [n] có trong tài liệu được cung cấp; không bịa điều luật, số tiền phạt hay nội dung.
- Nếu tài liệu không đủ căn cứ: answer nêu rõ, cited_indexes là [].
"""

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_CITATION_INDEX_RE = re.compile(r"\[(\d+)\]")
_NUMBERED_CHUNK_SPLIT_RE = re.compile(r"(?=\[\d+\]\n)")

_SESSION_TOKEN_EXHAUSTED_MSG = "Đã dùng hết token cho đoạn chat này nhé"
_BLOCKED_SESSION_STATUSES = frozenset({"deleted", "use_up_token"})


_llm: LLMProvider | None = None


def _get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider(llm_config)
    return _llm


def _chunks_to_context(chunks: list[Any], *, start_index: int = 1) -> str:
    parts: list[str] = []
    index = start_index
    for chunk in chunks:
        passage = BgeM3Reranker.passage_text(chunk, text_field="content_text")
        if not passage.strip():
            continue
        parts.append(f"[{index}]\n{passage}")
        index += 1
    return "\n\n".join(parts).strip()


def _format_ieee_citation(index: int, chunk: dict[str, Any]) -> str:
    """Một dòng tham chiếu kiểu IEEE numbered [n]."""
    doc_title = chunk.get("doc_title")
    if doc_title and str(doc_title).strip():
        doc_type = chunk.get("doc_type")
        suffix = f" ({doc_type})" if doc_type and str(doc_type).strip() else ""
        return f"[{index}] {str(doc_title).strip()}{suffix}, tài liệu người dùng tải lên"

    segments: list[str] = []
    for key in ("topic_title", "subject_title", "article_title", "chapter_title"):
        value = chunk.get(key)
        if value and str(value).strip():
            segments.append(str(value).strip())
    title = ", ".join(segments) if segments else "Văn bản pháp luật"
    link = chunk.get("source_link")
    if link and str(link).strip():
        return f"[{index}] {title}, {str(link).strip()}"
    return f"[{index}] {title}"


def _parse_llm_retrieval_response(raw: str | None) -> tuple[str | None, list[int]]:
    if not raw or not str(raw).strip():
        return None, []

    text = str(raw).strip()
    text = _JSON_FENCE_RE.sub("", text).strip()

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
        logger.warning("LLM retrieval response is not valid JSON; falling back to plain text")

    # Fallback: plain answer + trích [n] trong văn bản
    indexes = sorted({int(m) for m in _CITATION_INDEX_RE.findall(text)})
    return text, indexes


def _build_references(
    reranked_hits: list[dict[str, Any]],
    cited_indexes: list[int],
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    max_index = len(reranked_hits)
    for index in cited_indexes:
        if index < 1 or index > max_index:
            continue
        chunk = hit_to_api_chunk(reranked_hits[index - 1], include_rerank=True)
        ref = {
            "index": index,
            "ieee": _format_ieee_citation(index, chunk),
            **chunk,
        }
        references.append(ref)
    return references


def _rerank_hits(
    query: str,
    hits: list[dict[str, Any]],
    *,
    final_size: int,
    reranker: BgeM3Reranker | None = None,
) -> list[dict[str, Any]]:
    if not hits:
        return []
    limit = max(1, int(final_size))
    if reranker is not None:
        return reranker.rerank(
            query,
            hits,
            top_k=limit,
            text_field="content_text",
            include_titles=True,
        )
    if is_reranker_ready():
        return get_reranker().rerank(
            query,
            hits,
            top_k=limit,
            text_field="content_text",
            include_titles=True,
        )
    logger.warning("Reranker not ready; returning top hits by ES score")
    return hits[:limit]


def _generate_answer_with_citations(
    query: str,
    legal_context: str,
    *,
    user_upload_context: str | None = None,
) -> tuple[str | None, list[int]]:
    legal_context = (legal_context or "").strip()
    user_upload_context = (user_upload_context or "").strip()
    if not legal_context and not user_upload_context:
        return None, []

    parts = [f"Câu hỏi:\n{query.strip()}\n"]
    if legal_context:
        parts.append(
            f"Tài liệu tham chiếu pháp luật (trích dẫn theo số [n]):\n{legal_context}"
        )
    if user_upload_context:
        parts.append(
            "Nội dung tài liệu do người dùng tải lên "
            "(trích dẫn theo số [n] tiếp theo phần pháp luật nếu có):\n"
            f"{user_upload_context}"
        )
    user_content = "\n\n".join(parts)
    raw = _get_llm().chat_text(
        [{"role": "user", "content": user_content}],
        system_prompt=_RETRIEVAL_SYSTEM_PROMPT,
        max_tokens=2000,
        temperature=0.2,
    )
    answer, cited_indexes = _parse_llm_retrieval_response(raw)
    if answer:
        from_answer = {int(m) for m in _CITATION_INDEX_RE.findall(answer)}
        cited_indexes = sorted(set(cited_indexes) | from_answer)
    return answer, cited_indexes


def should_end_conversation(
    legal_context: str,
    user_upload_context: str,
) -> tuple[bool, str]:
    """
    Đếm token (tiktoken) của hai context.

    Nếu tổng > RETRIEVAL_CONTEXT_MAX_TOKENS: cắt ``legal_context`` (giữ user upload),
    trả về (True, legal_context_đã_cắt). Ngược lại (False, legal_context_gốc).
    """
    legal = (legal_context or "").strip()
    user = (user_upload_context or "").strip()
    total = count_tokens(legal) + count_tokens(user)
    if total <= RETRIEVAL_CONTEXT_MAX_TOKENS:
        return False, legal

    user_tokens = count_tokens(user)
    budget_for_legal = max(0, RETRIEVAL_CONTEXT_MAX_TOKENS - user_tokens)
    trimmed = _trim_legal_context_to_token_budget(legal, budget_for_legal)
    logger.warning(
        "should_end_conversation: context tokens {} > {}; legal trimmed to {} tokens",
        total,
        RETRIEVAL_CONTEXT_MAX_TOKENS,
        count_tokens(trimmed),
    )
    return True, trimmed


def _trim_legal_context_to_token_budget(legal_context: str, max_tokens: int) -> str:
    """Cắt context pháp luật theo từng khối [n], ưu tiên giữ chunk đầu."""
    if max_tokens <= 0:
        return ""
    text = (legal_context or "").strip()
    if not text:
        return ""
    if count_tokens(text) <= max_tokens:
        return text

    parts = [p for p in _NUMBERED_CHUNK_SPLIT_RE.split(text) if p.strip()]
    if not parts:
        return trim_text_to_token_budget(text, max_tokens)

    kept: list[str] = []
    used = 0
    for part in parts:
        part_tokens = count_tokens(part)
        if used + part_tokens <= max_tokens:
            kept.append(part)
            used += part_tokens
        else:
            break
    if kept:
        return "".join(kept).strip()
    return trim_text_to_token_budget(parts[0], max_tokens)


def _session_blocked_message(
    session_id: str | None,
    *,
    user_id: str | None = None,
) -> str | None:
    """Trả về thông báo lỗi nếu session deleted / use_up_token; None nếu được phép chat."""
    sid = _normalize_session_id(session_id)
    if not sid:
        return None

    session = ChatSessionService.get_session(sid)
    if not session:
        return None
    if user_id and session.user_id != user_id:
        raise PermissionError("Session does not belong to this user")
    if (session.status or "").strip() in _BLOCKED_SESSION_STATUSES:
        return _SESSION_TOKEN_EXHAUSTED_MSG
    return None


def _normalize_session_id(session_id: str | None) -> str | None:
    if session_id is None:
        return None
    s = str(session_id).strip()
    if s.lower() in ("", "null", "undefined", "none"):
        return None
    return s


def _normalize_id_list(ids: list[str] | None) -> list[str]:
    if not ids:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for raw in ids:
        s = str(raw).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _merge_unique_ids(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for raw in group:
            s = str(raw).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
    return out


def _document_ids_from_session_metadata(metadata: dict[str, Any] | None) -> list[str]:
    meta = metadata or {}
    doc_ids = [str(d).strip() for d in (meta.get("document_ids") or []) if str(d).strip()]
    if doc_ids:
        return list(dict.fromkeys(doc_ids))
    seen: set[str] = set()
    out: list[str] = []
    for item in meta.get("uploads") or []:
        if not isinstance(item, dict):
            continue
        did = str(item.get("document_id") or "").strip()
        if did and did not in seen:
            seen.add(did)
            out.append(did)
    return out


def _resolve_session_retrieval(
    session_id: str | None,
    *,
    user_id: str | None = None,
) -> tuple[str | None, list[str]]:
    """Trả về (retrieval_strategy, document_ids) từ chat_sessions.metadata."""
    sid = _normalize_session_id(session_id)
    if not sid:
        return None, []

    session = ChatSessionService.get_session(sid)
    if not session:
        logger.warning("admin_retrieve_and_answer: session not found id={}", sid)
        return None, []
    if user_id and session.user_id != user_id:
        raise PermissionError("Session does not belong to this user")
    if (session.status or "").strip() in _BLOCKED_SESSION_STATUSES:
        return None, []

    meta = session.metadata if isinstance(session.metadata, dict) else {}
    strategy = str(meta.get("retrieval_strategy") or "").strip() or None
    doc_ids = _document_ids_from_session_metadata(meta)
    return strategy, doc_ids


def admin_retrieve_and_answer(
    *,
    query: str,
    session_id: str | None = None,
    user_id: str | None = None,
    candidate_size: int = 100,
    similarity_threshold: float = 0.5,
    final_size: int = 5,
    keyword_weight: float = 0.3,
    field_weights: list[str] | None = None,
    topic_ids: list[str] | None = None,
    subject_ids: list[str] | None = None,
    extra_doc_ids: list[str] | None = None,
    reranker: BgeM3Reranker | None = None,
) -> dict[str, Any]:
    """Run search → rerank → LLM; trả về query, answer (có [n]), reference (chỉ nguồn đã trích)."""
    blocked = _session_blocked_message(session_id, user_id=user_id)
    if blocked:
        return {
            "query": query,
            "answer": blocked,
            "reference": [],
        }

    retrieval_strategy, document_ids = _resolve_session_retrieval(
        session_id, user_id=user_id
    )
    request_doc_ids = _normalize_id_list(extra_doc_ids)
    if request_doc_ids and retrieval_strategy == "load_in_context":
        before = len(document_ids)
        document_ids = _merge_unique_ids(document_ids, request_doc_ids)
        logger.info(
            "admin_retrieve_and_answer: merged request doc_ids extra={} "
            "document_ids {} -> {}",
            len(request_doc_ids),
            before,
            len(document_ids),
        )
    logger.info(
        "admin_retrieve_and_answer: session_id={} strategy={} document_ids={}",
        _normalize_session_id(session_id),
        retrieval_strategy,
        len(document_ids),
    )

    searcher = LexChunkSearch()
    candidates = searcher.search(
        query,
        candidate_size=candidate_size,
        similarity_threshold=similarity_threshold,
        keyword_weight=keyword_weight,
        field_weights=field_weights,
        topic_ids=topic_ids,
        subject_ids=subject_ids,
    )
    logger.info(
        "admin_retrieve_and_answer: es_candidates={} threshold={} final_size={}",
        len(candidates),
        similarity_threshold,
        final_size,
    )

    reranked = _rerank_hits(
        query,
        candidates,
        final_size=final_size,
        reranker=reranker,
    )

    user_doc_hits: list[dict[str, Any]] = []
    if retrieval_strategy == "load_in_context" and document_ids:
        user_doc_hits = searcher.retrieval_document(query, document_ids)
        logger.info(
            "admin_retrieve_and_answer: load_in_context user_chunks={}",
            len(user_doc_hits),
        )

    legal_context = _chunks_to_context(reranked)
    user_upload_context = ""
    if user_doc_hits:
        start = len(reranked) + 1 if reranked else 1
        user_upload_context = _chunks_to_context(user_doc_hits, start_index=start)

    hits_for_references = list(reranked) + list(user_doc_hits)
    end_conversation, legal_context = should_end_conversation(
        legal_context,
        user_upload_context,
    )
    sid = _normalize_session_id(session_id)
    if end_conversation and sid:
        ChatSessionService.mark_use_up_token(session_id=sid, user_id=user_id)

    answer, cited_indexes = _generate_answer_with_citations(
        query,
        legal_context,
        user_upload_context=user_upload_context or None,
    )
    references = _build_references(hits_for_references, cited_indexes)

    logger.info(
        "admin_retrieve_and_answer: cited_indexes={} references={}",
        cited_indexes,
        len(references),
    )

    return {
        "query": query,
        "answer": answer,
        "reference": references,
    }
