"""Parse user-uploaded files (PDF, DOCX, images) via Docling."""

from __future__ import annotations

import os
import tempfile
import threading
from contextlib import suppress
from pathlib import Path
from typing import Any

from api.utils.logger import setup_logging

logger = setup_logging()

SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx", ".jpg", ".jpeg", ".png"})

_docling_converter: Any = None
_docling_lock = threading.Lock()


def warmup_docling() -> None:
    """Preload Docling converter (OCR weights) once per process."""
    _get_docling_converter()


def _get_docling_converter() -> Any:
    global _docling_converter
    with _docling_lock:
        if _docling_converter is None:
            from docling.document_converter import DocumentConverter

            _docling_converter = DocumentConverter()
            logger.info("Docling DocumentConverter initialized")
        return _docling_converter


class DocDealingLoader:
    """Load file bytes or path into plain text / markdown using Docling."""

    @staticmethod
    def is_supported_suffix(suffix: str) -> bool:
        s = (suffix or "").lower().strip()
        if not s.startswith("."):
            s = f".{s}"
        return s in SUPPORTED_SUFFIXES

    @classmethod
    def parse_path(cls, path: str | Path) -> str:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")
        if not cls.is_supported_suffix(p.suffix):
            raise ValueError(
                f"Unsupported file type {p.suffix!r}; "
                f"allowed: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
            )
        converter = _get_docling_converter()
        result = converter.convert(str(p))
        text = result.document.export_to_markdown()
        return (text or "").strip()

    @classmethod
    def parse_bytes(cls, body: bytes, *, suffix: str) -> str:
        if not body:
            raise ValueError("Empty file")
        suf = (suffix or "").lower().strip()
        if not suf.startswith("."):
            suf = f".{suf}"
        if not cls.is_supported_suffix(suf):
            raise ValueError(
                f"Unsupported file type {suf!r}; "
                f"allowed: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
            )

        tmp_dir = Path(tempfile.gettempdir()) / "legalagent_docdealing"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(suffix=suf, dir=str(tmp_dir))
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            tmp_path.write_bytes(body)
            return cls.parse_path(tmp_path)
        finally:
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)
