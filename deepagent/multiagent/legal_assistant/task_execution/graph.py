from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.shared.checkpointer import get_checkpointer
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.task_execution.nodes import (
    assess_and_merge_user_input,
    fill_document_and_finalize,
    finalize_cancelled,
    hitl_form_fields_checkpoint,
    load_template_bytes,
    load_template_context,
    resolve_template_document,
    route_after_assess,
    route_after_field_hitl,
)


def build_graph(*, with_checkpointer: bool = True):
    builder = StateGraph(LegalAssistantState)
    builder.add_node("resolve_template_document", resolve_template_document)
    builder.add_node("load_template_bytes", load_template_bytes)
    builder.add_node("load_template_context", load_template_context)
    builder.add_node("assess_and_merge_user_input", assess_and_merge_user_input)
    builder.add_node("hitl_form_fields_checkpoint", hitl_form_fields_checkpoint)
    builder.add_node("fill_document_and_finalize", fill_document_and_finalize)
    builder.add_node("finalize_cancelled", finalize_cancelled)

    builder.add_edge(START, "resolve_template_document")
    builder.add_edge("resolve_template_document", "load_template_bytes")
    builder.add_edge("load_template_bytes", "load_template_context")
    builder.add_edge("load_template_context", "assess_and_merge_user_input")
    builder.add_conditional_edges(
        "assess_and_merge_user_input",
        route_after_assess,
        {
            "hitl_fields": "hitl_form_fields_checkpoint",
            "fill_and_finalize": "fill_document_and_finalize",
        },
    )
    builder.add_conditional_edges(
        "hitl_form_fields_checkpoint",
        route_after_field_hitl,
        {
            "assess": "assess_and_merge_user_input",
            "end_cancel": "finalize_cancelled",
        },
    )
    builder.add_edge("fill_document_and_finalize", END)
    builder.add_edge("finalize_cancelled", END)

    checkpointer = get_checkpointer() if with_checkpointer else None
    return builder.compile(checkpointer=checkpointer)
