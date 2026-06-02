from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.information.nodes import (
    compose_final_answer,
    expand_query_for_next_rag,
    rag_retrieve,
    reason_if_enough,
    rewrite_query_from_history,
    route_after_reason,
    synthesize_with_web,
    web_search_tavily,
)
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState


def build_graph():
    builder = StateGraph(LegalAssistantState)
    builder.add_node("rewrite_query_from_history", rewrite_query_from_history)
    builder.add_node("rag_retrieve", rag_retrieve)
    builder.add_node("reason_if_enough", reason_if_enough)
    builder.add_node("expand_query_for_next_rag", expand_query_for_next_rag)
    builder.add_node("web_search_tavily", web_search_tavily)
    builder.add_node("synthesize_with_web", synthesize_with_web)
    builder.add_node("compose_final_answer", compose_final_answer)

    builder.add_edge(START, "rewrite_query_from_history")
    builder.add_edge("rewrite_query_from_history", "rag_retrieve")
    builder.add_edge("rag_retrieve", "reason_if_enough")

    builder.add_conditional_edges(
        "reason_if_enough",
        route_after_reason,
        {
            "enough": "compose_final_answer",
            "retry_rag": "expand_query_for_next_rag",
            "fallback_web": "web_search_tavily",
        },
    )
    builder.add_edge("expand_query_for_next_rag", "rag_retrieve")
    builder.add_edge("web_search_tavily", "synthesize_with_web")
    builder.add_edge("synthesize_with_web", END)
    builder.add_edge("compose_final_answer", END)
    return builder.compile()
