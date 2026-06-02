from __future__ import annotations

from typing import Any


def ensure_output_shape(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload or {}
    return {
        "query": data.get("query", ""),
        "answer": data.get("answer"),
        "reference": data.get("reference") or [],
    }


def has_answer(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    answer = payload.get("answer")
    return bool(answer and str(answer).strip())
