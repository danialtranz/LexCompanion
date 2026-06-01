"""Recursive sliding-window split for user document text (~tokens with char proxy)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from langchain_text_splitters.base import TextSplitter

from deepagent.core.text_splitters.legal_article_split import split_long_content

# ~4 chars per token (mixed VI/EN); override via env if needed.
_CHARS_PER_TOKEN = max(1, int(os.getenv("USER_DOC_CHARS_PER_TOKEN", "4")))
_CHUNK_TOKENS = max(256, int(os.getenv("USER_DOC_CHUNK_TOKENS", "2500")))
_OVERLAP_TOKENS = max(0, int(os.getenv("USER_DOC_CHUNK_OVERLAP_TOKENS", "400")))

CHUNK_TARGET = _CHUNK_TOKENS * _CHARS_PER_TOKEN
CHUNK_MIN = max(CHUNK_TARGET - 100, int(CHUNK_TARGET * 0.96))
CHUNK_MAX = CHUNK_TARGET + 100
CHUNK_OVERLAP = _OVERLAP_TOKENS * _CHARS_PER_TOKEN
SPLIT_THRESHOLD = CHUNK_TARGET
BOUNDARY_WINDOW = 100


@dataclass(frozen=True)
class UserDocumentChunk:
    text: str
    chunk_order: int | None
    chunk_parent_id: str | None
    max_chunks: int


class UserDocumentSplitter(TextSplitter):
    """Split parsed document text into ~2500-token chunks with ~400-token overlap."""

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
        content = text or ""
        if len(content) < self.split_threshold:
            return [content]
        return split_long_content(
            content,
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
        document_id: str,
    ) -> list[UserDocumentChunk]:
        pieces = self.split_text(text)
        max_chunks = len(pieces)
        parent = document_id if max_chunks > 1 else None
        return [
            UserDocumentChunk(
                text=piece,
                chunk_order=index if max_chunks > 1 else None,
                chunk_parent_id=parent,
                max_chunks=max_chunks,
            )
            for index, piece in enumerate(pieces)
        ]
