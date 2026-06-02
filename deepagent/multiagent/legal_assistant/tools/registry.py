from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .calculators import estimate_fine_range
from .document_tools import build_basic_document_draft
from .legal_retrieval import run_legal_retrieval
from .web_search import run_web_search

ToolFn = Callable[..., dict[str, Any]]

TOOL_REGISTRY: dict[str, ToolFn] = {
    "legal_retrieval": run_legal_retrieval,
    "web_search": run_web_search,
    "calculators": estimate_fine_range,
    "document_tools": build_basic_document_draft,
}


def get_tool(tool_name: str) -> ToolFn:
    return TOOL_REGISTRY[tool_name]
