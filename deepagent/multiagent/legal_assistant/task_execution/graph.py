from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.task_execution.nodes import (
    run_task_execution_flow,
)


def build_graph():
    builder = StateGraph(LegalAssistantState)
    builder.add_node("run_task_execution_flow", run_task_execution_flow)
    builder.add_edge(START, "run_task_execution_flow")
    builder.add_edge("run_task_execution_flow", END)
    return builder.compile()
