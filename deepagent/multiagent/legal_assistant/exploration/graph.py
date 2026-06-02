from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.exploration.nodes import run_exploration_flow
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState


def build_graph():
    builder = StateGraph(LegalAssistantState)
    builder.add_node("run_exploration_flow", run_exploration_flow)
    builder.add_edge(START, "run_exploration_flow")
    builder.add_edge("run_exploration_flow", END)
    return builder.compile()
