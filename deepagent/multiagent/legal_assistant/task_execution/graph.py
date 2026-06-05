from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.shared.checkpointer import get_checkpointer
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.task_execution.nodes import (
    advance_or_seek_chunk,
    assess_current_chunk,
    fill_document_and_finalize,
    finalize_cancelled,
    hitl_form_fields_checkpoint,
    init_document_chunks,
    init_hitl_groups,
    load_docx_template_context,
    load_template_bytes,
    load_template_context,
    resolve_template_document,
    route_after_advance_or_seek,
    route_after_chunk_assess,
    route_after_field_hitl,
    route_after_load_template,
)


def build_graph(*, with_checkpointer: bool = True):
    builder = StateGraph(LegalAssistantState)
    builder.add_node("resolve_template_document", resolve_template_document)
    builder.add_node("load_template_bytes", load_template_bytes)
    builder.add_node("load_docx_template_context", load_docx_template_context)
    builder.add_node("load_template_context", load_template_context)
    builder.add_node("init_hitl_groups", init_hitl_groups)
    builder.add_node("init_document_chunks", init_document_chunks)
    builder.add_node("assess_current_chunk", assess_current_chunk)
    builder.add_node("advance_or_seek_chunk", advance_or_seek_chunk)
    builder.add_node("hitl_form_fields_checkpoint", hitl_form_fields_checkpoint)
    builder.add_node("fill_document_and_finalize", fill_document_and_finalize)
    builder.add_node("finalize_cancelled", finalize_cancelled)

    builder.add_edge(START, "resolve_template_document")
    builder.add_edge("resolve_template_document", "load_template_bytes")
    builder.add_conditional_edges(
        "load_template_bytes",
        route_after_load_template,
        {
            "docx_native": "load_docx_template_context",
            "markdown_reference": "load_template_context",
        },
    )
    builder.add_edge("load_docx_template_context", "init_hitl_groups")
    builder.add_edge("init_hitl_groups", "assess_current_chunk")
    builder.add_edge("load_template_context", "init_document_chunks")
    builder.add_edge("init_document_chunks", "assess_current_chunk")
    builder.add_conditional_edges(
        "assess_current_chunk",
        route_after_chunk_assess,
        {
            "hitl_fields": "hitl_form_fields_checkpoint",
            "advance_or_seek": "advance_or_seek_chunk",
            "fill_and_finalize": "fill_document_and_finalize",
        },
    )
    builder.add_conditional_edges(
        "advance_or_seek_chunk",
        route_after_advance_or_seek,
        {
            "assess_chunk": "assess_current_chunk",
            "fill_and_finalize": "fill_document_and_finalize",
        },
    )
    builder.add_conditional_edges(
        "hitl_form_fields_checkpoint",
        route_after_field_hitl,
        {
            "assess_chunk": "assess_current_chunk",
            "end_cancel": "finalize_cancelled",
        },
    )
    builder.add_edge("fill_document_and_finalize", END)
    builder.add_edge("finalize_cancelled", END)

    checkpointer = get_checkpointer() if with_checkpointer else None
    return builder.compile(checkpointer=checkpointer)
