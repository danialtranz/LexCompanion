from __future__ import annotations

from typing import Any

from deepagent.multiagent.legal_assistant.tools.calculators import estimate_fine_range


def compute_decision_estimate(query: str) -> dict[str, Any]:
    return estimate_fine_range(query=query)
