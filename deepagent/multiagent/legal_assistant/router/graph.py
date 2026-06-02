from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.router.nodes import pass_through_router
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState


def build_graph():
    builder = StateGraph(LegalAssistantState)
    builder.add_node("pass_through_router", pass_through_router)
    builder.add_edge(START, "pass_through_router")
    builder.add_edge("pass_through_router", END)
    return builder.compile()
