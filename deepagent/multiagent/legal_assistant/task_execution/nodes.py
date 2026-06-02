from __future__ import annotations

from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.task_execution.templates import select_template
from deepagent.multiagent.legal_assistant.task_execution.validators import (
    validate_document_draft,
)
from deepagent.multiagent.legal_assistant.tools.document_tools import (
    build_basic_document_draft,
)


def run_task_execution_flow(state: LegalAssistantState) -> LegalAssistantState:
    query = state.get("user_query", "")
    template_id = select_template(query)
    draft = build_basic_document_draft(query=query, doc_type=template_id)
    validation = validate_document_draft(draft)

    next_state = dict(state)
    next_state["task_checklist"] = [
        "Xác nhận thông tin định danh các bên.",
        "Xác nhận ngày tháng, địa điểm, chữ ký.",
    ]
    next_state["output"] = {
        "query": query,
        "answer": draft.get("content"),
        "reference": [],
        "template_id": template_id,
        "draft": draft,
        "validation": validation,
        "task_checklist": next_state["task_checklist"],
    }
    next_state["response"] = next_state["output"]["answer"]
    return next_state
