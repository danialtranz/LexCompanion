from __future__ import annotations

import json

from api.utils.llm_client import LLMProvider, config as llm_config
from api.utils.logger import setup_logging

from .constants import CITATION_INDEX_RE, JSON_FENCE_RE, RETRIEVAL_SYSTEM_PROMPT

logger = setup_logging()

_llm: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider(llm_config)
    return _llm


def parse_llm_retrieval_response(raw: str | None) -> tuple[str | None, list[int]]:
    if not raw or not str(raw).strip():
        return None, []

    text = str(raw).strip()
    text = JSON_FENCE_RE.sub("", text).strip()

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

    indexes = sorted({int(m) for m in CITATION_INDEX_RE.findall(text)})
    return text, indexes


def generate_answer_with_citations(
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
    raw = get_llm().chat_text(
        [{"role": "user", "content": user_content}],
        system_prompt=RETRIEVAL_SYSTEM_PROMPT,
        max_tokens=2000,
        temperature=0.2,
    )
    answer, cited_indexes = parse_llm_retrieval_response(raw)
    if answer:
        from_answer = {int(m) for m in CITATION_INDEX_RE.findall(answer)}
        cited_indexes = sorted(set(cited_indexes) | from_answer)
    return answer, cited_indexes
