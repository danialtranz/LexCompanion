from __future__ import annotations

from typing import Any


def score_options(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Placeholder scoring: giữ nguyên thứ tự và thêm điểm mặc định.
    scored: list[dict[str, Any]] = []
    for idx, item in enumerate(options, start=1):
        scored.append({**item, "score": max(1, 100 - idx * 5)})
    return scored
