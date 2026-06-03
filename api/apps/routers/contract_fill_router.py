from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from fastapi import Query

from api.apps.controllers.contract_draft_controller import stream_contract_draft
from api.apps.controllers.contract_fill_controller import contract_fill, contract_fill_stream
from api.apps.middleware.jwt_auth import CurrentUser

router = APIRouter(prefix="/v1/user", tags=["contract-fill"])


class ContractFillRequest(BaseModel):
    query: str = Field(..., description="Yêu cầu hoặc câu trả lời bổ sung field")
    template_document_id: str | None = Field(
        None,
        description="document_id tùy chọn; nếu bỏ trống dùng session uploads / HITL",
    )
    session_id: str | None = Field(None, description="Chat session để multi-turn + lưu draft")
    thread_id: str | None = Field(None, description="Checkpoint thread_id từ response trước")
    resume: dict | None = Field(None, description="HITL resume {action, payload}")
    stream: bool = Field(False, description="Bật SSE text/event-stream")


@router.post("/contract/fill")
def contract_fill_route(user: CurrentUser, payload: ContractFillRequest = Body(...)):
    if payload.stream:
        return contract_fill_stream(
            user=user,
            query=payload.query,
            template_document_id=payload.template_document_id,
            session_id=payload.session_id,
            thread_id=payload.thread_id,
            resume=payload.resume,
        )
    return contract_fill(
        user=user,
        query=payload.query,
        template_document_id=payload.template_document_id,
        session_id=payload.session_id,
        thread_id=payload.thread_id,
        resume=payload.resume,
    )


@router.get("/contract/draft")
def contract_draft_download_route(
    user: CurrentUser,
    session_id: str = Query(..., description="Session id with contract_fill metadata"),
):
    return stream_contract_draft(user=user, session_id=session_id)
