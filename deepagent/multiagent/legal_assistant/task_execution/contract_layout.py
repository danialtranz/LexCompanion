from __future__ import annotations

import re
from difflib import SequenceMatcher

from deepagent.core.document_loaders.docdealing import LayoutTextItem

_DOTS_RE = re.compile(r"\.{3,}|_{3,}|…+")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def find_bbox_for_anchor(
    anchor_text: str,
    layout_items: list[LayoutTextItem],
    *,
    min_score: float = 0.45,
) -> dict[str, float | int] | None:
    """Match anchor snippet to nearest Docling text block."""
    anchor = (anchor_text or "").strip()
    if not anchor or not layout_items:
        return None

    best: LayoutTextItem | None = None
    best_score = 0.0
    for item in layout_items:
        score = similarity(anchor, item.text)
        if anchor in item.text or item.text in anchor:
            score = max(score, 0.75)
        if score > best_score:
            best_score = score
            best = item

    if best is None or best_score < min_score:
        return None
    return {
        "page_no": best.page_no,
        "l": best.bbox["l"],
        "t": best.bbox["t"],
        "r": best.bbox["r"],
        "b": best.bbox["b"],
        "coord_origin": best.coord_origin,
        "match_score": round(best_score, 3),
    }


def detect_placeholder_in_text(text: str) -> bool:
    return bool(_DOTS_RE.search(text or ""))
