from __future__ import annotations

from typing import Any

from api.utils.token_count import (
    RETRIEVAL_CONTEXT_MAX_TOKENS,
    count_tokens,
    trim_text_to_token_budget,
)
from api.utils.logger import setup_logging
from deepagent.core.rerank.rerank import BgeM3Reranker

from .constants import NUMBERED_CHUNK_SPLIT_RE

logger = setup_logging()


def chunks_to_context(chunks: list[Any], *, start_index: int = 1) -> str:
    parts: list[str] = []
    index = start_index
    for chunk in chunks:
        passage = BgeM3Reranker.passage_text(chunk, text_field="content_text")
        if not passage.strip():
            continue
        parts.append(f"[{index}]\n{passage}")
        index += 1
    return "\n\n".join(parts).strip()


def trim_legal_context_to_token_budget(legal_context: str, max_tokens: int) -> str:
    """Cắt context pháp luật theo từng khối [n], ưu tiên giữ chunk đầu."""
    if max_tokens <= 0:
        return ""
    text = (legal_context or "").strip()
    if not text:
        return ""
    if count_tokens(text) <= max_tokens:
        return text

    parts = [p for p in NUMBERED_CHUNK_SPLIT_RE.split(text) if p.strip()]
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
    trimmed = trim_legal_context_to_token_budget(legal, budget_for_legal)
    logger.warning(
        "should_end_conversation: context tokens {} > {}; legal trimmed to {} tokens",
        total,
        RETRIEVAL_CONTEXT_MAX_TOKENS,
        count_tokens(trimmed),
    )
    return True, trimmed
