from __future__ import annotations

from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState


def pass_through_router(state: LegalAssistantState) -> LegalAssistantState:
    """
    Router graph placeholder.
    Bản hiện tại giữ intent đã có từ orchestrator.
    """
    return state
