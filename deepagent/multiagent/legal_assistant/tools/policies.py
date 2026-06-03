from __future__ import annotations

from deepagent.multiagent.legal_assistant.shared.state import IntentType

INTENT_ALLOWED_TOOLS: dict[IntentType, list[str]] = {
    "information": ["legal_retrieval"],
    "decision": ["legal_retrieval", "calculators"],
    "task_execution": ["document_tools", "legal_retrieval"],
    "problem_solving": ["legal_retrieval", "calculators"],
    "exploration": ["legal_retrieval", "web_search", "calculators"],
    "communication_normal": [],
}
