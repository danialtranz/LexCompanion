from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.communication_normal.nodes import (
    run_communication_response,
)
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState


def build_graph():
    builder = StateGraph(LegalAssistantState)
    builder.add_node("run_communication_response", run_communication_response)
    builder.add_edge(START, "run_communication_response")
    builder.add_edge("run_communication_response", END)
    return builder.compile()
