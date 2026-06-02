from __future__ import annotations

from typing import Any

from deepagent.multiagent.legal_assistant.decision.graph import build_graph as build_decision_graph
from deepagent.multiagent.legal_assistant.exploration.graph import (
    build_graph as build_exploration_graph,
)
from deepagent.multiagent.legal_assistant.information.graph import (
    build_graph as build_information_graph,
)
from deepagent.multiagent.legal_assistant.problem_solving.graph import (
    build_graph as build_problem_solving_graph,
)
from deepagent.multiagent.legal_assistant.shared.state import IntentType, LegalAssistantState
from deepagent.multiagent.legal_assistant.task_execution.graph import (
    build_graph as build_task_execution_graph,
)

_GRAPH_BUILDERS = {
    "information": build_information_graph,
    "decision": build_decision_graph,
    "task_execution": build_task_execution_graph,
    "problem_solving": build_problem_solving_graph,
    "exploration": build_exploration_graph,
}

_GRAPH_CACHE: dict[IntentType, Any] = {}


def get_graph(intent: IntentType):
    if intent not in _GRAPH_CACHE:
        _GRAPH_CACHE[intent] = _GRAPH_BUILDERS[intent]()
    return _GRAPH_CACHE[intent]


def run_graph(intent: IntentType, state: LegalAssistantState) -> LegalAssistantState:
    graph = get_graph(intent)
    return graph.invoke(state)
