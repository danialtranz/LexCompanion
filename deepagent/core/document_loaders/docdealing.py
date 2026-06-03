"""Parse user-uploaded files (PDF, DOCX, images) via Docling."""

from __future__ import annotations

import os
import tempfile
import threading
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from api.utils.logger import setup_logging

logger = setup_logging()

SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx", ".jpg", ".jpeg", ".png"})

_docling_converter: Any = None
_docling_lock = threading.Lock()


@dataclass(slots=True)
class LayoutTextItem:
    text: str
    page_no: int
    bbox: dict[str, float]
    coord_origin: str = "TOPLEFT"


@dataclass(slots=True)
class DocParseResult:
    markdown: str
    layout_items: list[LayoutTextItem] = field(default_factory=list)
    page_count: int = 1
    suffix: str = ""


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


def _extract_layout_items(doc: Any) -> list[LayoutTextItem]:
    items: list[LayoutTextItem] = []
    texts = getattr(doc, "texts", None) or []
    for raw in texts:
        text = (getattr(raw, "text", None) or "").strip()
        if not text:
            continue
        prov_list = getattr(raw, "prov", None) or []
        if not prov_list:
            continue
        prov = prov_list[0]
        bbox = getattr(prov, "bbox", None)
        if bbox is None:
            continue
        page_no = int(getattr(prov, "page_no", 1) or 1)
        origin = getattr(bbox, "coord_origin", None)
        items.append(
            LayoutTextItem(
                text=text,
                page_no=page_no,
                bbox={
                    "l": float(bbox.l),
                    "t": float(bbox.t),
                    "r": float(bbox.r),
                    "b": float(bbox.b),
                },
                coord_origin=str(origin) if origin is not None else "TOPLEFT",
            )
        )
    return items


def _page_count_from_doc(doc: Any) -> int:
    pages = getattr(doc, "pages", None)
    if pages is not None:
        try:
            return max(1, len(pages))
        except TypeError:
            pass
    nums = [it.page_no for it in _extract_layout_items(doc)]
    return max(nums) if nums else 1


class DocDealingLoader:
    """Load file bytes or path into plain text / markdown using Docling."""

    @staticmethod
    def is_supported_suffix(suffix: str) -> bool:
        s = (suffix or "").lower().strip()
        if not s.startswith("."):
            s = f".{s}"
        return s in SUPPORTED_SUFFIXES

    @classmethod
    def parse_document(cls, path: str | Path) -> DocParseResult:
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
        doc = result.document
        markdown = (doc.export_to_markdown() or "").strip()
        layout_items = _extract_layout_items(doc)
        return DocParseResult(
            markdown=markdown,
            layout_items=layout_items,
            page_count=_page_count_from_doc(doc),
            suffix=p.suffix.lower(),
        )

    @classmethod
    def parse_path(cls, path: str | Path) -> str:
        return cls.parse_document(path).markdown

    @classmethod
    def parse_bytes(cls, body: bytes, *, suffix: str) -> str:
        return cls.parse_bytes_full(body, suffix=suffix).markdown

    @classmethod
    def parse_bytes_full(cls, body: bytes, *, suffix: str) -> DocParseResult:
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
            parsed = cls.parse_document(tmp_path)
            parsed.suffix = suf
            return parsed
        finally:
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)
