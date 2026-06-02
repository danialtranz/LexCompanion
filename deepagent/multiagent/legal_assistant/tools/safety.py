from __future__ import annotations

from typing import Any


def validate_tool_output(tool_name: str, output: dict[str, Any] | None) -> dict[str, Any]:
    data = output or {}
    data["tool_name"] = tool_name
    data["is_valid"] = isinstance(output, dict)
    return data
