from __future__ import annotations

from typing import Any, Literal

from langgraph.types import interrupt

from deepagent.core.document_loaders.docdealing import LayoutTextItem
from deepagent.core.hitl.checkpoint import build_hitl_interrupt, parse_human_resume
from deepagent.core.hitl.form_hitl import (
    assess_form_for_hitl,
    compose_form_clarification_answer,
)
from deepagent.multiagent.legal_assistant.shared.state import LegalAssistantState
from deepagent.multiagent.legal_assistant.task_execution.contract_tools import (
    DOCX_SUFFIX,
    enrich_schema_with_layout,
    extract_form_fields,
    layout_items_to_dicts,
    render_filled_document,
    save_draft_to_minio,
)
from deepagent.multiagent.legal_assistant.task_execution.docx_field_extract import (
    extract_fields_from_docx_llm,
)
from deepagent.multiagent.legal_assistant.task_execution.hitl_groups import (
    group_excerpts,
    map_fields_to_group_indices,
)
from deepagent.multiagent.legal_assistant.task_execution.draft_preview import (
    attach_draft_preview,
    build_draft_preview_markdown,
    persist_incremental_draft_to_storage,
)
from deepagent.multiagent.legal_assistant.task_execution.document_chunks import (
    all_required_filled,
    fields_for_chunk,
    is_chunk_complete,
    map_fields_to_chunk_indices,
    refine_assessment_for_chunk,
    split_markdown_into_chunks,
)
from deepagent.multiagent.legal_assistant.task_execution.session_documents import (
    resolve_doc_ids_from_state,
)
from deepagent.multiagent.legal_assistant.task_execution.template_loader import (
    load_template_into_state,
)
from deepagent.multiagent.legal_assistant.task_execution.validators import (
    validate_document_draft,
)

RouteAfterLoadTemplate = Literal["docx_native", "markdown_reference"]
RouteAfterChunkAssess = Literal["hitl_fields", "advance_or_seek", "fill_and_finalize"]
RouteAfterAdvanceOrSeek = Literal["assess_chunk", "fill_and_finalize"]
RouteAfterFieldHitl = Literal["assess_chunk", "end_cancel"]


def _layout_from_state(state: LegalAssistantState) -> list[LayoutTextItem]:
    items: list[LayoutTextItem] = []
    for raw in state.get("layout_items") or []:
        if not isinstance(raw, dict):
            continue
        bbox = raw.get("bbox") or {}
        items.append(
            LayoutTextItem(
                text=str(raw.get("text") or ""),
                page_no=int(raw.get("page_no") or 1),
                bbox={
                    "l": float(bbox.get("l", 0)),
                    "t": float(bbox.get("t", 0)),
                    "r": float(bbox.get("r", 0)),
                    "b": float(bbox.get("b", 0)),
                },
                coord_origin=str(raw.get("coord_origin") or "TOPLEFT"),
            )
        )
    return items


def _thread_id_from_state(state: LegalAssistantState) -> str | None:
    return state.get("thread_id")  # type: ignore[attr-defined]


def _extract_document_id(resume_raw: Any, allowed_ids: list[str]) -> str | None:
    parsed = parse_human_resume(resume_raw)
    payload = parsed.get("payload") or {}
    doc_id = (
        payload.get("document_id")
        or payload.get("template_document_id")
        or payload.get("text")
    )
    if doc_id:
        doc_id = str(doc_id).strip()
    if doc_id and allowed_ids and doc_id not in allowed_ids:
        # Cho phép id mới sau upload (không có trong list cũ)
        if len(allowed_ids) == 0:
            return doc_id
    if doc_id and (not allowed_ids or doc_id in allowed_ids):
        return doc_id
    if allowed_ids and parsed.get("action") == "select":
        idx = payload.get("index")
        try:
            return allowed_ids[int(idx)]
        except (TypeError, ValueError, IndexError):
            pass
    return doc_id if doc_id else None


def resolve_template_document(state: LegalAssistantState) -> LegalAssistantState:
    """
    Bước đầu task_execution: resolve doc_ids hoặc HITL chọn/upload template.
    """
    next_state = dict(state)
    user_id = str(next_state.get("user_id") or "").strip()
    doc_ids, uploads = resolve_doc_ids_from_state(
        doc_ids=next_state.get("doc_ids"),
        session_uploads=next_state.get("session_uploads"),
        session_id=next_state.get("session_id"),
        user_id=user_id or None,
    )
    next_state["session_uploads"] = uploads  # type: ignore[typeddict-unknown-key]

    tid = _thread_id_from_state(next_state)

    if len(doc_ids) == 1:
        next_state["template_document_id"] = doc_ids[0]
        next_state["doc_ids"] = doc_ids
        next_state["answer_mode"] = "template_selected"
        return next_state

    if len(doc_ids) > 1:
        upload_options = uploads or [
            {"document_id": d, "name": d, "doc_type": ""} for d in doc_ids
        ]
        resume_raw = interrupt(
            build_hitl_interrupt(
                kind="select_upload",
                message=(
                    "Bạn đã tải lên nhiều tài liệu trong phiên này. "
                    "Vui lòng chọn mẫu hợp đồng bạn muốn điền."
                ),
                hitl={
                    "actions": ["select", "reject"],
                    "uploads": upload_options,
                    "options": doc_ids,
                },
                resume={
                    "endpoint": "POST /v1/user/user_chat",
                    "required_fields": ["document_id"],
                    "example": {
                        "action": "select",
                        "payload": {"document_id": doc_ids[0]},
                    },
                },
                thread_id=tid,
            )
        )
        selected = _extract_document_id(resume_raw, doc_ids)
        if not selected:
            raise ValueError("resume.payload.document_id is required")
        next_state["template_document_id"] = selected
        next_state["doc_ids"] = [selected]
        next_state["answer_mode"] = "template_selected"
        return next_state

    # Không có tài liệu
    resume_raw = interrupt(
        build_hitl_interrupt(
            kind="request_upload",
            message=(
                "Chưa có mẫu hợp đồng trong phiên làm việc. "
                "Vui lòng tải lên file DOCX, PDF hoặc ảnh chụp hợp đồng "
                "(POST /v1/user/upload kèm session_id), sau đó gửi lại yêu cầu "
                "hoặc resume với document_id."
            ),
            hitl={
                "actions": ["upload", "reject"],
                "uploads": [],
                "upload_endpoint": "/v1/user/upload",
            },
            resume={
                "endpoint": "POST /v1/user/user_chat",
                "required_fields": ["document_id"],
                "example": {
                    "action": "upload",
                    "payload": {"document_id": "<document_id sau upload>"},
                },
            },
            thread_id=tid,
        )
    )
    selected = _extract_document_id(resume_raw, [])
    if not selected:
        raise ValueError(
            "document_id required: upload file then resume with document_id"
        )
    next_state["template_document_id"] = selected
    next_state["doc_ids"] = [selected]
    next_state["answer_mode"] = "template_selected"
    return next_state


def load_template_bytes(state: LegalAssistantState) -> LegalAssistantState:
    next_state = dict(state)
    doc_id = str(next_state.get("template_document_id") or "").strip()
    user_id = str(next_state.get("user_id") or "").strip()
    if not doc_id or not user_id:
        raise ValueError("template_document_id and user_id are required")

    loaded = load_template_into_state(user_id=user_id, document_id=doc_id)
    next_state.update(loaded)  # type: ignore[arg-type]
    next_state["answer_mode"] = "template_loaded"
    return next_state


def _ensure_template_in_state(state: LegalAssistantState) -> LegalAssistantState:
    """
    Checkpoint HITL thường không giữ được ``bytes`` trong state.
    Tải lại mẫu từ storage khi thiếu ``_template_bytes`` hoặc ``template_markdown``.
    """
    next_state = dict(state)
    mode = next_state.get("template_mode") or "markdown_reference"
    body = next_state.get("working_docx_bytes") or next_state.get("_template_bytes")
    markdown = (next_state.get("template_markdown") or "").strip()
    schema = list(next_state.get("form_schema") or [])

    if mode == "docx_native":
        if isinstance(body, (bytes, bytearray)) and schema:
            next_state["working_docx_bytes"] = bytes(body)
            return next_state
    elif isinstance(body, (bytes, bytearray)) and markdown:
        return next_state

    doc_id = str(next_state.get("template_document_id") or "").strip()
    user_id = str(next_state.get("user_id") or "").strip()
    if not doc_id or not user_id:
        return next_state

    loaded = load_template_into_state(user_id=user_id, document_id=doc_id)
    for key, value in loaded.items():
        if key in ("_template_bytes", "working_docx_bytes"):
            next_state[key] = value  # type: ignore[literal-required]
        elif not next_state.get(key):
            next_state[key] = value  # type: ignore[literal-required]
        elif key == "template_markdown" and not markdown:
            next_state[key] = value  # type: ignore[literal-required]
    if next_state.get("template_mode") == "docx_native" and next_state.get("_template_bytes"):
        next_state["working_docx_bytes"] = next_state["_template_bytes"]
    return next_state


def route_after_load_template(state: LegalAssistantState) -> RouteAfterLoadTemplate:
    mode = state.get("template_mode")
    suffix = (state.get("template_suffix") or "").lower()
    if mode == "docx_native" or suffix == DOCX_SUFFIX:
        return "docx_native"
    return "markdown_reference"


def load_docx_template_context(state: LegalAssistantState) -> LegalAssistantState:
    """DOCX native: LLM phân tích cấu trúc gốc → field schema + hitl_groups."""
    next_state = dict(state)
    body = next_state.get("working_docx_bytes") or next_state.get("_template_bytes")
    if not isinstance(body, (bytes, bytearray)):
        raise ValueError("DOCX template bytes missing in state")

    schema = list(next_state.get("form_schema") or [])
    groups = list(next_state.get("hitl_groups") or [])
    blocks = list(next_state.get("structured_blocks") or [])

    if not schema:
        schema, groups, blocks = extract_fields_from_docx_llm(bytes(body))

    next_state["template_mode"] = "docx_native"
    next_state["form_schema"] = schema
    next_state["hitl_groups"] = groups
    next_state["structured_blocks"] = blocks
    next_state["working_docx_bytes"] = bytes(body)
    if not next_state.get("filled_values"):
        next_state["filled_values"] = {}
    next_state["answer_mode"] = "detecting_fields" if schema else "awaiting_template"
    return next_state


def init_hitl_groups(state: LegalAssistantState) -> LegalAssistantState:
    """Khởi tạo nhóm HITL từ schema DOCX (không cắt markdown)."""
    next_state = dict(state)
    groups = list(next_state.get("hitl_groups") or [])
    blocks = list(next_state.get("structured_blocks") or [])
    schema = list(next_state.get("form_schema") or [])

    if not groups and schema:
        keys = [str(f.get("id") or "") for f in schema]
        mid = max(1, len(keys) // 2)
        groups = [
            {"group_id": 0, "title": "Phần 1", "field_keys": keys[:mid]},
            {"group_id": 1, "title": "Phần 2", "field_keys": keys[mid:]},
        ]
        next_state["hitl_groups"] = groups

    excerpts = group_excerpts(groups, blocks, schema) if groups else [""]
    field_map = map_fields_to_group_indices(schema, groups) if schema else {}
    next_state["template_chunks"] = excerpts
    next_state["current_chunk_index"] = 0
    next_state["field_chunk_index"] = field_map
    next_state["answer_mode"] = "chunks_ready"
    return next_state


def load_template_context(state: LegalAssistantState) -> LegalAssistantState:
    next_state = dict(state)
    markdown = (next_state.get("template_markdown") or "").strip()
    schema = list(next_state.get("form_schema") or [])

    if not schema and markdown:
        layout = _layout_from_state(next_state)
        schema = extract_form_fields(markdown, layout or None)
        if layout:
            schema = enrich_schema_with_layout(schema, layout)
        next_state["form_schema"] = schema
        next_state["layout_items"] = layout_items_to_dicts(layout)

    if not next_state.get("filled_values"):
        next_state["filled_values"] = {}

    next_state["answer_mode"] = "detecting_fields" if schema else "awaiting_template"
    return next_state


def init_document_chunks(state: LegalAssistantState) -> LegalAssistantState:
    """Cắt template_markdown thành chunks và map field → chunk."""
    next_state = dict(state)
    markdown = (next_state.get("template_markdown") or "").strip()
    schema = list(next_state.get("form_schema") or [])
    chunks = split_markdown_into_chunks(markdown)
    if not chunks:
        chunks = [""]
    field_map = map_fields_to_chunk_indices(schema, markdown, chunks) if schema else {}
    next_state["template_chunks"] = chunks
    next_state["current_chunk_index"] = 0
    next_state["field_chunk_index"] = field_map
    next_state["answer_mode"] = "chunks_ready"
    return next_state


def _chunk_progress(state: LegalAssistantState) -> tuple[int, int]:
    chunks = list(state.get("template_chunks") or [])
    idx = int(state.get("current_chunk_index") or 0)
    return idx, max(len(chunks), 1)


def _current_chunk_excerpt(state: LegalAssistantState) -> str:
    chunks = list(state.get("template_chunks") or [])
    idx = int(state.get("current_chunk_index") or 0)
    if not chunks:
        return ""
    return chunks[min(idx, len(chunks) - 1)]


def assess_current_chunk(state: LegalAssistantState) -> LegalAssistantState:
    """Đánh giá và merge giá trị chỉ cho các field thuộc chunk hiện tại."""
    next_state = dict(state)
    query = (
        next_state.get("resolved_user_request")
        or next_state.get("user_query")
        or ""
    ).strip()
    schema = list(next_state.get("form_schema") or [])
    filled = dict(next_state.get("filled_values") or {})
    field_map = dict(next_state.get("field_chunk_index") or {})
    chunk_index = int(next_state.get("current_chunk_index") or 0)
    chunk_fields = fields_for_chunk(schema, field_map, chunk_index)

    if not chunk_fields:
        next_state["answer_mode"] = "chunk_complete"
        next_state["form_hitl"] = {"is_complete": True, "missing_field_ids": []}
        return next_state

    assessment = assess_form_for_hitl(
        user_message=query,
        form_schema=chunk_fields,
        filled_values=filled,
        chat_history=next_state.get("chat_history"),
        document_excerpt=_current_chunk_excerpt(next_state),
    )
    proposed = assessment.get("proposed_values") or {}
    merged = {**filled, **proposed}
    for f in schema:
        fid = str(f.get("id") or "")
        if fid and merged.get(fid):
            f["value"] = merged[fid]

    assessment = refine_assessment_for_chunk(
        dict(assessment),
        form_schema=schema,
        field_chunk_index=field_map,
        chunk_index=chunk_index,
        merged_values=merged,
    )

    next_state["filled_values"] = merged
    next_state["form_schema"] = schema
    next_state["form_hitl"] = assessment
    next_state["needs_user_clarification"] = bool(
        assessment.get("needs_user_clarification")
    )
    next_state["missing_facts"] = list(assessment.get("missing_facts") or [])
    next_state["clarification_questions"] = list(
        assessment.get("clarification_questions") or []
    )
    next_state["partial_answer_preface"] = str(
        assessment.get("partial_answer_preface") or ""
    )
    next_state["hitl_used"] = True

    chunk_idx, chunk_total = _chunk_progress(next_state)
    if assessment.get("is_complete") or is_chunk_complete(
        schema, field_map, chunk_index, merged
    ):
        next_state["answer_mode"] = "chunk_complete"
    elif assessment.get("needs_user_clarification"):
        next_state["answer_mode"] = "needs_user_clarification"
    else:
        next_state["answer_mode"] = "chunk_complete"
    next_state["chunk_progress"] = {
        "current": chunk_idx + 1,
        "total": chunk_total,
    }
    # Chỉ lưu MinIO khi chunk tự hoàn thành (không chờ HITL).
    # Sau HITL đã lưu ở hitl_form_fields_checkpoint — tránh 3 bản/vòng.
    came_from_hitl = (state.get("answer_mode") == "after_field_hitl")
    if assessment.get("needs_user_clarification") or came_from_hitl:
        return attach_draft_preview(next_state)  # type: ignore[return-value]
    return persist_incremental_draft_to_storage(
        attach_draft_preview(next_state)  # type: ignore[arg-type]
    )


def advance_or_seek_chunk(state: LegalAssistantState) -> LegalAssistantState:
    """Sau khi chunk hiện tại xong: nhảy tới chunk kế tiếp còn thiếu hoặc kết thúc."""
    next_state = dict(state)
    schema = list(next_state.get("form_schema") or [])
    field_map = dict(next_state.get("field_chunk_index") or {})
    filled = dict(next_state.get("filled_values") or {})
    chunks = list(next_state.get("template_chunks") or [])
    idx = int(next_state.get("current_chunk_index") or 0)

    if all_required_filled(schema, filled):
        next_state["answer_mode"] = "all_chunks_done"
        return next_state

    for j in range(idx + 1, len(chunks)):
        if not is_chunk_complete(schema, field_map, j, filled):
            next_state["current_chunk_index"] = j
            next_state["answer_mode"] = "chunk_advanced"
            return next_state

    for j in range(0, len(chunks)):
        if not is_chunk_complete(schema, field_map, j, filled):
            next_state["current_chunk_index"] = j
            next_state["answer_mode"] = "chunk_advanced"
            return next_state

    next_state["answer_mode"] = "all_chunks_done"
    return next_state


def route_after_chunk_assess(state: LegalAssistantState) -> RouteAfterChunkAssess:
    if state.get("answer_mode") == "needs_user_clarification" or state.get(
        "needs_user_clarification"
    ):
        return "hitl_fields"

    schema = list(state.get("form_schema") or [])
    field_map = dict(state.get("field_chunk_index") or {})
    filled = dict(state.get("filled_values") or {})
    idx = int(state.get("current_chunk_index") or 0)

    if not is_chunk_complete(schema, field_map, idx, filled):
        return "hitl_fields"

    if all_required_filled(schema, filled):
        return "fill_and_finalize"

    return "advance_or_seek"


def route_after_advance_or_seek(
    state: LegalAssistantState,
) -> RouteAfterAdvanceOrSeek:
    if state.get("answer_mode") == "all_chunks_done":
        return "fill_and_finalize"
    return "assess_chunk"


def hitl_form_fields_checkpoint(state: LegalAssistantState) -> LegalAssistantState:
    """Checkpoint HITL — chờ user bổ sung field thuộc chunk hiện tại."""
    next_state = dict(state)
    hitl = next_state.get("form_hitl") or {}
    message = compose_form_clarification_answer(hitl)  # type: ignore[arg-type]
    schema = list(next_state.get("form_schema") or [])
    field_map = dict(next_state.get("field_chunk_index") or {})
    chunk_index = int(next_state.get("current_chunk_index") or 0)
    chunk_fields = fields_for_chunk(schema, field_map, chunk_index)
    chunk_idx, chunk_total = _chunk_progress(next_state)
    missing_ids = list(hitl.get("missing_field_ids") or [])
    chunk_preview = _current_chunk_excerpt(next_state)
    draft_preview = build_draft_preview_markdown(next_state)

    progress_line = (
        f"\n\n(Đoạn {chunk_idx + 1}/{chunk_total} của văn bản mẫu — "
        "vui lòng bổ sung thông tin cho phần này.)"
    )
    message = (message or "").strip() + progress_line

    resume_raw = interrupt(
        build_hitl_interrupt(
            kind="form_fields",
            message=message,
            hitl={
                "actions": ["approve", "edit", "reject"],
                "form_schema": chunk_fields,
                "filled_values": next_state.get("filled_values") or {},
                "missing_field_ids": missing_ids,
                "clarification_questions": next_state.get("clarification_questions")
                or [],
                "chunk_index": chunk_index,
                "chunk_total": chunk_total,
                "chunk_preview": chunk_preview[:4000],
                "draft_preview_markdown": draft_preview[:12000],
                "filled_values": dict(next_state.get("filled_values") or {}),
            },
            resume={
                "endpoint": "POST /v1/user/user_chat",
                "required_fields": ["action"],
                "example": {
                    "action": "edit",
                    "payload": {
                        "field_values": {"ben_a_ten": "Nguyễn Văn A"},
                        "text": "Bên A là Nguyễn Văn A",
                    },
                },
            },
            thread_id=_thread_id_from_state(next_state),
        )
    )

    parsed = parse_human_resume(resume_raw)
    action = parsed.get("action") or "edit"
    payload = parsed.get("payload") or {}

    if action == "reject":
        next_state["answer_mode"] = "cancelled"
        next_state["response"] = "Đã hủy điền mẫu theo yêu cầu của bạn."
        return next_state

    merged = dict(next_state.get("filled_values") or {})
    field_values = payload.get("field_values")
    if isinstance(field_values, dict):
        for k, v in field_values.items():
            if v is not None and str(v).strip():
                merged[str(k)] = str(v).strip()

    text_answer = str(payload.get("text") or "").strip()
    if text_answer and action in ("edit", "approve"):
        reassess = assess_form_for_hitl(
            user_message=text_answer,
            form_schema=chunk_fields,
            filled_values=merged,
            chat_history=next_state.get("chat_history"),
            document_excerpt=chunk_preview,
        )
        merged.update(reassess.get("proposed_values") or {})

    next_state["filled_values"] = merged
    next_state["resolved_user_request"] = text_answer or next_state.get("resolved_user_request")
    next_state["answer_mode"] = "after_field_hitl"
    return persist_incremental_draft_to_storage(
        attach_draft_preview(next_state)  # type: ignore[arg-type]
    )


def route_after_field_hitl(state: LegalAssistantState) -> RouteAfterFieldHitl:
    if state.get("answer_mode") == "cancelled":
        return "end_cancel"
    return "assess_chunk"


def finalize_cancelled(state: LegalAssistantState) -> LegalAssistantState:
    next_state = dict(state)
    next_state["output"] = {
        "query": next_state.get("user_query", ""),
        "answer": next_state.get("response") or "Đã hủy.",
        "reference": [],
        "answer_mode": "cancelled",
    }
    return next_state


def fill_document_and_finalize(state: LegalAssistantState) -> LegalAssistantState:
    next_state = _ensure_template_in_state(state)
    mode = next_state.get("template_mode") or "markdown_reference"
    if mode == "docx_native":
        body = next_state.get("_template_bytes") or next_state.get("working_docx_bytes")
    else:
        body = next_state.get("working_docx_bytes") or next_state.get("_template_bytes")
    markdown = (next_state.get("template_markdown") or "").strip()
    if mode != "docx_native" and not markdown and not isinstance(body, (bytes, bytearray)):
        raise ValueError(
            "Template not loaded in state (missing template_markdown after reload)"
        )
    if mode == "docx_native" and not isinstance(body, (bytes, bytearray)):
        raise ValueError("DOCX template bytes missing for finalize")

    suffix = (next_state.get("template_suffix") or DOCX_SUFFIX).lower()
    filled = dict(next_state.get("filled_values") or {})
    schema = list(next_state.get("form_schema") or [])

    out_bytes, out_suffix = render_filled_document(
        body=bytes(body) if isinstance(body, (bytes, bytearray)) else b"",
        suffix=suffix,
        filled_values=filled,
        form_schema=schema,
        template_markdown=markdown,
        template_mode=mode,
    )
    if mode == "docx_native":
        next_state["working_docx_bytes"] = out_bytes

    version = int(next_state.get("draft_version") or 0) + 1
    tenant = str(next_state.get("contract_tenant_id") or "")
    kb_id = str(next_state.get("contract_kb_id") or "contract")
    doc_id = str(next_state.get("template_document_id") or "template")
    prefix = f"{kb_id}/contract_fill/{doc_id}"

    draft_key = save_draft_to_minio(
        tenant_id=tenant,
        kb_id=kb_id,
        body=out_bytes,
        suffix=out_suffix,
        draft_key_prefix=prefix,
        version=version,
    )

    draft_meta = {
        "doc_type": out_suffix.lstrip("."),
        "title": f"Filled contract v{version}",
        "content": _summary_filled(schema, filled),
    }
    validation = validate_document_draft(draft_meta)

    source_label = (
        "mẫu DOCX gốc"
        if mode == "docx_native"
        else f"mẫu tham chiếu ({suffix})"
    )
    summary = (
        f"Đã soạn thảo văn bản từ {source_label}, "
        f"điền {len([k for k, v in filled.items() if v])} trường. "
        f"Bản DOCX phiên bản {version} đã sẵn sàng — tải qua GET /v1/user/contract/draft."
    )

    next_state["draft_version"] = version
    next_state["draft_object_key"] = draft_key
    next_state["draft_output_suffix"] = out_suffix
    next_state["answer_mode"] = "completed"
    next_state["task_checklist"] = [
        "Xác nhận thông tin các bên trên bản in.",
        "Kiểm tra ngày tháng, chữ ký trước khi ký chính thức.",
    ]
    chunks = list(next_state.get("template_chunks") or [])
    preview_md = build_draft_preview_markdown(next_state)
    next_state["draft_preview_markdown"] = preview_md
    next_state["output"] = {
        "query": next_state.get("resolved_user_request") or next_state.get("user_query", ""),
        "answer": summary,
        "reference": [],
        "answer_mode": "completed",
        "template_document_id": next_state.get("template_document_id"),
        "form_schema": schema,
        "filled_values": filled,
        "validation": validation,
        "draft_version": version,
        "draft_object_key": draft_key,
        "draft_output_suffix": out_suffix,
        "draft_preview_markdown": preview_md,
        "task_checklist": next_state["task_checklist"],
        "chunk_total": len(chunks),
    }
    next_state["response"] = summary
    return next_state


def _summary_filled(schema: list[dict], filled: dict[str, str]) -> str:
    lines = []
    for f in schema:
        fid = str(f.get("id") or "")
        label = str(f.get("label") or fid)
        val = filled.get(fid) or "(trống)"
        lines.append(f"{label}: {val}")
    return "\n".join(lines)
