from __future__ import annotations

from typing import Any

from langgraph.types import Command

from deepagent.core.hitl.checkpoint import (
    default_thread_id,
    format_graph_invoke_result,
)
from deepagent.multiagent.legal_assistant.communication_normal.graph import (
    build_graph as build_communication_normal_graph,
)
from deepagent.multiagent.legal_assistant.decision.graph import build_graph as build_decision_graph
from deepagent.multiagent.legal_assistant.exploration.graph import (
    build_graph as build_exploration_graph,
)
from deepagent.multiagent.legal_assistant.information.graph import (
    build_graph as build_information_graph,
)
from deepagent.multiagent.legal_assistant.problem_solving.graph import (
    build_graph as build_problem_solving_graph,
)
from deepagent.multiagent.legal_assistant.shared.state import IntentType, LegalAssistantState
from deepagent.multiagent.legal_assistant.task_execution.graph import (
    build_graph as build_task_execution_graph,
)
from deepagent.multiagent.legal_assistant.task_execution.session_documents import (
    resolve_doc_ids_from_state,
)

_GRAPH_BUILDERS = {
    "information": build_information_graph,
    "decision": build_decision_graph,
    "problem_solving": build_problem_solving_graph,
    "exploration": build_exploration_graph,
    "communication_normal": build_communication_normal_graph,
}

_GRAPH_CACHE: dict[IntentType, Any] = {}
_TASK_EXECUTION_GRAPH: Any | None = None


def get_graph(intent: IntentType):
    if intent == "task_execution":
        return get_task_execution_graph()
    if intent not in _GRAPH_CACHE:
        _GRAPH_CACHE[intent] = _GRAPH_BUILDERS[intent]()
    return _GRAPH_CACHE[intent]


def get_task_execution_graph():
    global _TASK_EXECUTION_GRAPH
    if _TASK_EXECUTION_GRAPH is None:
        _TASK_EXECUTION_GRAPH = build_task_execution_graph(with_checkpointer=True)
    return _TASK_EXECUTION_GRAPH


def run_graph(intent: IntentType, state: LegalAssistantState) -> LegalAssistantState:
    if intent == "task_execution":
        envelope = invoke_task_execution_graph(
            state,
            thread_id=state.get("thread_id"),
            resume=None,
            query_fallback=state.get("user_query"),
        )
        if envelope.get("status") == "waiting_human":
            return _envelope_to_state(state, envelope)
        return _envelope_to_state(state, envelope)

    graph = get_graph(intent)
    return graph.invoke(state)


def invoke_task_execution_graph(
    state: LegalAssistantState,
    *,
    thread_id: str | None = None,
    resume: Any | None = None,
    query_fallback: str | None = None,
) -> dict[str, Any]:
    """
    Chạy task_execution với checkpoint; trả envelope chuẩn cho FE.
    """
    graph = get_task_execution_graph()
    tid = thread_id or default_thread_id(
        session_id=state.get("session_id"),
        user_id=state.get("user_id"),
        intent="task_execution",
    )
    config = {"configurable": {"thread_id": tid}}
    snap = graph.get_state(config)

    if resume is not None:
        raw = graph.invoke(Command(resume=resume), config)
    elif snap.next:
        fallback = {
            "action": "edit",
            "payload": {"text": (query_fallback or "").strip()},
        }
        raw = graph.invoke(Command(resume=fallback), config)
    else:
        run_state = dict(state)
        run_state["thread_id"] = tid
        if (
            "session_uploads" not in run_state
            and run_state.get("session_id")
        ):
            ids, uploads = resolve_doc_ids_from_state(
                doc_ids=run_state.get("doc_ids"),
                session_id=run_state.get("session_id"),
                user_id=run_state.get("user_id"),
            )
            run_state["doc_ids"] = ids or None
            run_state["session_uploads"] = uploads
        raw = graph.invoke(run_state, config)

    if isinstance(raw, dict):
        raw.setdefault("thread_id", tid)
    return format_graph_invoke_result(raw, thread_id=tid)


def _envelope_to_state(
    base: LegalAssistantState, envelope: dict[str, Any]
) -> LegalAssistantState:
    out = dict(base)
    out["thread_id"] = envelope.get("thread_id")
    if envelope.get("status") == "waiting_human":
        out["answer_mode"] = "waiting_human"
        out["response"] = envelope.get("message")
        out["output"] = {
            "status": envelope.get("status"),
            "message": envelope.get("message"),
            "hitl": envelope.get("hitl"),
            "resume": envelope.get("resume"),
            "thread_id": envelope.get("thread_id"),
            "answer": envelope.get("message"),
            "reference": [],
        }
        return out  # type: ignore[return-value]

    data = envelope.get("output") or envelope
    out["response"] = envelope.get("message") or envelope.get("answer")
    out["output"] = data if isinstance(data, dict) else {"answer": out["response"]}
    out["answer_mode"] = envelope.get("answer_mode") or data.get("answer_mode")
    for key in (
        "form_schema",
        "filled_values",
        "template_document_id",
        "draft_version",
        "draft_object_key",
    ):
        if envelope.get(key) is not None:
            out[key] = envelope[key]  # type: ignore[literal-required]
        elif isinstance(data, dict) and data.get(key) is not None:
            out[key] = data[key]  # type: ignore[literal-required]
    return out  # type: ignore[return-value]
