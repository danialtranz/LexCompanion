from __future__ import annotations

from typing import Any


def build_basic_document_draft(*, query: str, doc_type: str = "general", **_: Any) -> dict[str, Any]:
    """
    Placeholder document tool cho intent task_execution.
    """
    return {
        "doc_type": doc_type,
        "title": f"Draft - {doc_type}",
        "content": f"Mẫu nháp được tạo từ yêu cầu: {query}",
    }
