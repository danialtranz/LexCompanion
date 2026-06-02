from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

IntentType = Literal[
    "information",
    "decision",
    "task_execution",
    "problem_solving",
    "exploration",
]


@dataclass(slots=True)
class RoutingDecision:
    intent: IntentType
    confidence: float = 1.0
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChatOrchestratorInput:
    query: str
    session_id: str | None = None
    user_id: str | None = None
    candidate_size: int = 100
    similarity_threshold: float = 0.5
    final_size: int = 5
    keyword_weight: float = 0.3
    field_weights: list[str] | None = None
    topic_ids: list[str] | None = None
    subject_ids: list[str] | None = None
    doc_ids: list[str] | None = None
    reranker: Any | None = None
