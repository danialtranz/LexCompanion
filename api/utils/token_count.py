"""Accurate token counting via tiktoken."""

from __future__ import annotations

import os
import threading
from typing import Any

_encoding: Any = None
_encoding_lock = threading.Lock()

# Session retrieval: <= threshold → load full doc in context; > threshold → multi-hop RAG.
CONTEXT_TOKEN_THRESHOLD = max(1, int(os.getenv("USER_DOC_CONTEXT_TOKEN_THRESHOLD", "30000")))

# Max tokens for legal + user upload context sent to the LLM in one turn.
RETRIEVAL_CONTEXT_MAX_TOKENS = max(
    1024, int(os.getenv("RETRIEVAL_CONTEXT_MAX_TOKENS", "128000"))
)


def _resolve_encoding_name() -> str:
    raw = (os.getenv("TIKTOKEN_ENCODING") or os.getenv("TIKTOKEN_MODEL") or "").strip()
    if raw:
        return raw
    llm_model = (os.getenv("LLM_MODEL") or "").strip()
    if llm_model:
        return llm_model
    return "cl100k_base"


def _get_encoding():
    global _encoding
    with _encoding_lock:
        if _encoding is not None:
            return _encoding
        import tiktoken

        name = _resolve_encoding_name()
        try:
            _encoding = tiktoken.get_encoding(name)
        except ValueError:
            _encoding = tiktoken.encoding_for_model(name)
        return _encoding


def count_tokens(text: str) -> int:
    """Return token count for ``text`` (0 for empty)."""
    if not text or not str(text).strip():
        return 0
    return len(_get_encoding().encode(str(text)))


def trim_text_to_token_budget(text: str, max_tokens: int) -> str:
    """Truncate ``text`` to at most ``max_tokens`` (tiktoken), prefer keeping leading content."""
    if max_tokens <= 0:
        return ""
    content = str(text or "")
    if not content.strip():
        return ""
    enc = _get_encoding()
    ids = enc.encode(content)
    if len(ids) <= max_tokens:
        return content
    return enc.decode(ids[:max_tokens])


def retrieval_strategy_for_token_count(token_count: int) -> str:
    """
    <= CONTEXT_TOKEN_THRESHOLD → load_in_context
    > CONTEXT_TOKEN_THRESHOLD → multi_retrieval_hop
    """
    if token_count > CONTEXT_TOKEN_THRESHOLD:
        return "multi_retrieval_hop"
    return "load_in_context"
