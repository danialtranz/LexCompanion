from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver

_CHECKPOINTER: InMemorySaver | None = None


def get_checkpointer() -> InMemorySaver:
    global _CHECKPOINTER
    if _CHECKPOINTER is None:
        _CHECKPOINTER = InMemorySaver()
    return _CHECKPOINTER
