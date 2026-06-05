from __future__ import annotations

from typing import Any
from uuid import uuid4

HITL_STATUS_WAITING = "waiting_human"
HITL_STATUS_COMPLETED = "completed"


def default_thread_id(*, session_id: str | None, user_id: str | None, intent: str) -> str:
    sid = (session_id or "anon").strip()
    uid = (user_id or "anon").strip()
    return f"{uid}:{sid}:{intent}"


def build_hitl_interrupt(
    *,
    kind: str,
    message: str,
    hitl: dict[str, Any],
    resume: dict[str, Any],
    thread_id: str | None = None,
) -> dict[str, Any]:
    """
    Payload truyền vào langgraph.interrupt(); orchestrator bọc thêm thread_id.
    """
    return {
        "status": HITL_STATUS_WAITING,
        "message": message,
        "hitl": {
            "kind": kind,
            "interrupt_id": uuid4().hex,
            **hitl,
        },
        "resume": resume,
        "thread_id": thread_id,
    }


def build_completed_envelope(
    *,
    message: str,
    thread_id: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "status": HITL_STATUS_COMPLETED,
        "message": message,
        "thread_id": thread_id,
        "hitl": None,
        "resume": None,
    }
    if data:
        payload.update(data)
        if "answer" not in payload and message:
            payload["answer"] = message
    return payload


def _interrupt_value(raw: Any) -> dict[str, Any]:
    if hasattr(raw, "value"):
        val = raw.value
    else:
        val = raw
    return dict(val) if isinstance(val, dict) else {"message": str(val)}


def format_graph_invoke_result(
    result: dict[str, Any],
    *,
    thread_id: str,
) -> dict[str, Any]:
    """
    Chuẩn hóa output cho FE: waiting_human | completed.
    """
    interrupts = result.get("__interrupt__")
    if interrupts:
        first = interrupts[0] if isinstance(interrupts, (list, tuple)) else interrupts
        core = _interrupt_value(first)
        hitl = core.get("hitl") or {}
        envelope: dict[str, Any] = {
            "status": HITL_STATUS_WAITING,
            "message": core.get("message") or "",
            "hitl": hitl,
            "resume": core.get("resume") or {},
            "thread_id": thread_id,
            "query": result.get("user_query"),
            "answer_mode": result.get("answer_mode"),
        }
        preview = (
            core.get("draft_preview_markdown")
            or hitl.get("draft_preview_markdown")
            or result.get("draft_preview_markdown")
        )
        if preview:
            envelope["draft_preview_markdown"] = preview
        filled = result.get("filled_values") or hitl.get("filled_values")
        if filled:
            envelope["filled_values"] = filled
        for key in (
            "draft_object_key",
            "draft_version",
            "draft_output_suffix",
            "contract_tenant_id",
            "template_document_id",
        ):
            if result.get(key):
                envelope[key] = result[key]
        return envelope

    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    message = (
        output.get("answer")
        or result.get("response")
        or ""
    )
    envelope = build_completed_envelope(
        message=str(message),
        thread_id=thread_id,
        data={
            "query": output.get("query") or result.get("user_query"),
            "answer": message,
            "reference": output.get("reference") or [],
            "output": output,
            "answer_mode": result.get("answer_mode") or output.get("answer_mode"),
            "form_schema": result.get("form_schema") or output.get("form_schema"),
            "filled_values": result.get("filled_values") or output.get("filled_values"),
            "template_document_id": result.get("template_document_id")
            or output.get("template_document_id"),
            "draft_version": result.get("draft_version") or output.get("draft_version"),
            "draft_object_key": result.get("draft_object_key")
            or output.get("draft_object_key"),
            "draft_preview_markdown": result.get("draft_preview_markdown")
            or output.get("draft_preview_markdown"),
            "draft_output_suffix": result.get("draft_output_suffix")
            or output.get("draft_output_suffix"),
            "contract_tenant_id": result.get("contract_tenant_id")
            or output.get("contract_tenant_id"),
        },
    )
    return envelope


def parse_human_resume(resume: Any) -> dict[str, Any]:
    """Chuẩn hóa payload resume từ FE."""
    if resume is None:
        return {}
    if isinstance(resume, dict):
        action = str(resume.get("action") or "edit").strip().lower()
        payload = resume.get("payload")
        if not isinstance(payload, dict):
            payload = {k: v for k, v in resume.items() if k not in ("action", "payload")}
        return {"action": action, "payload": payload}
    text = str(resume).strip()
    if not text:
        return {}
    return {"action": "edit", "payload": {"text": text, "document_id": text}}
