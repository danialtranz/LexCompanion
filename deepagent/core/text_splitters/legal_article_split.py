"""Split long legal article content_text for Elasticsearch lex_chunks indexing.

Inspired by docling-style sliding-window chunking: fixed target size with overlap
and boundary-aware cuts (prefer sentence ends near the target window).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_text_splitters.base import TextSplitter

# Default thresholds aligned with phapdien legal_articles corpus.
SPLIT_THRESHOLD = 2500
CHUNK_TARGET = 2500
CHUNK_MIN = 2400
CHUNK_MAX = 2600
CHUNK_OVERLAP = 400
BOUNDARY_WINDOW = 100


@dataclass(frozen=True)
class LegalArticleContentChunk:
    """One ES-ready chunk derived from a legal_articles.content_text row."""

    text: str
    order: int | None
    parent_chunk_id: str | None
    max_chunks: int


def _find_period_split_end(
    text: str,
    start: int,
    ideal_end: int,
    text_len: int,
    *,
    chunk_min: int = CHUNK_MIN,
    chunk_max: int = CHUNK_MAX,
    boundary_window: int = BOUNDARY_WINDOW,
) -> int:
    """Pick split end index (exclusive) near ``ideal_end``, preferring ``.`` boundaries."""
    if ideal_end >= text_len:
        return text_len

    min_end = min(start + chunk_min, text_len)
    max_end = min(start + chunk_max, text_len)
    win_lo = max(min_end, ideal_end - boundary_window)
    win_hi = min(max_end, ideal_end + boundary_window)

    for pos in range(min(win_hi, text_len - 1), win_lo - 1, -1):
        if text[pos] == ".":
            candidate = pos + 1
            if min_end <= candidate <= max_end:
                return candidate

    for pos in range(win_lo, min(win_hi + 1, text_len)):
        if text[pos] == ".":
            candidate = pos + 1
            if min_end <= candidate <= max_end:
                return candidate

    return min(start + CHUNK_TARGET, text_len)


def split_long_content(
    text: str,
    *,
    chunk_target: int = CHUNK_TARGET,
    chunk_min: int = CHUNK_MIN,
    chunk_max: int = CHUNK_MAX,
    overlap: int = CHUNK_OVERLAP,
    boundary_window: int = BOUNDARY_WINDOW,
) -> list[str]:
    """Split ``text`` into ~2400–2600 char chunks with ``overlap`` char carry-over."""
    content = text or ""
    if not content:
        return [""]

    chunks: list[str] = []
    start = 0
    text_len = len(content)

    while start < text_len:
        remaining = text_len - start
        if remaining <= CHUNK_MAX:
            chunks.append(content[start:])
            break

        ideal_end = start + chunk_target
        end = _find_period_split_end(
            content,
            start,
            ideal_end,
            text_len,
            chunk_min=chunk_min,
            chunk_max=chunk_max,
            boundary_window=boundary_window,
        )
        if end <= start:
            end = min(start + chunk_target, text_len)

        chunks.append(content[start:end])
        if end >= text_len:
            break

        next_start = end - overlap
        start = end if next_start <= start else next_start

    return chunks


class LegalArticleContentSplitter(TextSplitter):
    """Split legal_articles.content_text when content_char_len >= split threshold."""

    def __init__(
        self,
        *,
        split_threshold: int = SPLIT_THRESHOLD,
        chunk_target: int = CHUNK_TARGET,
        chunk_min: int = CHUNK_MIN,
        chunk_max: int = CHUNK_MAX,
        overlap: int = CHUNK_OVERLAP,
        boundary_window: int = BOUNDARY_WINDOW,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.split_threshold = split_threshold
        self.chunk_target = chunk_target
        self.chunk_min = chunk_min
        self.chunk_max = chunk_max
        self.overlap = overlap
        self.boundary_window = boundary_window

    def split_text(self, text: str) -> list[str]:
        if len(text or "") < self.split_threshold:
            return [text or ""]
        return split_long_content(
            text,
            chunk_target=self.chunk_target,
            chunk_min=self.chunk_min,
            chunk_max=self.chunk_max,
            overlap=self.overlap,
            boundary_window=self.boundary_window,
        )

    def split_with_metadata(
        self,
        text: str,
        *,
        article_id: str,
        content_char_len: int | None = None,
    ) -> list[LegalArticleContentChunk]:
        """Return chunks with order / parent_chunk_id / max_chunks for lex_chunks index."""
        length = content_char_len if content_char_len is not None else len(text or "")
        if length < self.split_threshold:
            return [
                LegalArticleContentChunk(
                    text=text or "",
                    order=None,
                    parent_chunk_id=None,
                    max_chunks=1,
                )
            ]

        pieces = split_long_content(
            text,
            chunk_target=self.chunk_target,
            chunk_min=self.chunk_min,
            chunk_max=self.chunk_max,
            overlap=self.overlap,
            boundary_window=self.boundary_window,
        )
        max_chunks = len(pieces)
        return [
            LegalArticleContentChunk(
                text=piece,
                order=index,
                parent_chunk_id=article_id,
                max_chunks=max_chunks,
            )
            for index, piece in enumerate(pieces)
        ]
