from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.decision.nodes import run_decision_flow
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState


def build_graph():
    builder = StateGraph(LegalAssistantState)
    builder.add_node("run_decision_flow", run_decision_flow)
    builder.add_edge(START, "run_decision_flow")
    builder.add_edge("run_decision_flow", END)
    return builder.compile()
