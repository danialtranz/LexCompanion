from __future__ import annotations

from typing import Any


def build_basic_document_draft(*, query: str, doc_type: str = "general", **_: Any) -> dict[str, Any]:
    """Legacy helper; contract fill dùng task_execution graph + contract_tools."""
    return {
        "doc_type": doc_type,
        "title": f"Draft - {doc_type}",
        "content": f"Mẫu nháp được tạo từ yêu cầu: {query}",
    }
