from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.problem_solving.nodes import (
    run_problem_solving_flow,
)
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState


def build_graph():
    builder = StateGraph(LegalAssistantState)
    builder.add_node("run_problem_solving_flow", run_problem_solving_flow)
    builder.add_edge(START, "run_problem_solving_flow")
    builder.add_edge("run_problem_solving_flow", END)
    return builder.compile()
