from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from deepagent.multiagent.legal_assistant.information.nodes import (
    compose_final_answer,
    compose_uncited_fallback,
    compose_user_clarification,
    plan_rag_search_queries,
    rag_retrieve,
    reason_if_enough,
    route_after_reason,
    synthesize_with_web,
    web_search_tavily,
)
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState


def build_graph():
    builder = StateGraph(LegalAssistantState)
    builder.add_node("rag_retrieve", rag_retrieve)
    builder.add_node("reason_if_enough", reason_if_enough)
    builder.add_node("plan_rag_search_queries", plan_rag_search_queries)
    builder.add_node("web_search_tavily", web_search_tavily)
    builder.add_node("synthesize_with_web", synthesize_with_web)
    builder.add_node("compose_final_answer", compose_final_answer)
    builder.add_node("compose_user_clarification", compose_user_clarification)
    builder.add_node("compose_uncited_fallback", compose_uncited_fallback)

    builder.add_edge(START, "rag_retrieve")
    builder.add_edge("rag_retrieve", "reason_if_enough")

    builder.add_conditional_edges(
        "reason_if_enough",
        route_after_reason,
        {
            "enough": "compose_final_answer",
            "ask_user": "compose_user_clarification",
            "retry_rag": "plan_rag_search_queries",
            "fallback_web": "web_search_tavily",
            "uncited_fallback": "compose_uncited_fallback",
        },
    )
    builder.add_edge("plan_rag_search_queries", "rag_retrieve")
    builder.add_edge("web_search_tavily", "synthesize_with_web")
    builder.add_edge("synthesize_with_web", "reason_if_enough")
    builder.add_edge("compose_user_clarification", END)
    builder.add_edge("compose_uncited_fallback", END)
    builder.add_edge("compose_final_answer", END)
    return builder.compile()
