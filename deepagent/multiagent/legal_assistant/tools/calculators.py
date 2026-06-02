from __future__ import annotations

from typing import Any


def estimate_fine_range(*, query: str, **_: Any) -> dict[str, Any]:
    """
    Placeholder calculator cho intent decision/problem_solving.
    """
    return {
        "query": query,
        "estimate": {"min": None, "max": None, "currency": "VND"},
        "assumptions": ["Chưa có đủ dữ kiện để tính chính xác."],
    }
