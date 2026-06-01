from fastapi import APIRouter, Body, File, Form, Query, Request, UploadFile
from pydantic import Field

from api.apps.controllers.chat_controller import (
    delete_user_chat_session,
    get_user_chat_session_messages,
    list_user_chat_sessions,
    upload_user_file,
)
from api.apps.controllers.doc_controller import admin_doc_retrieval
from api.apps.middleware.jwt_auth import CurrentUser
from api.apps.routers.admin_doc_routers import AdminRetrievalRequest

router = APIRouter(prefix="/v1/user", tags=["user-chat"])


class UserChatRequest(AdminRetrievalRequest):
    stream: bool = Field(
        False,
        description="Dự phòng streaming; hiện tại luôn trả JSON qua admin_doc_retrieval",
    )


@router.delete("/chat")
def user_delete_chat_route(
    user: CurrentUser,
    session_id: str = Query(..., description="Chat session id to delete"),
):
    return delete_user_chat_session(user=user, session_id=session_id)


@router.get("/sessions")
def user_list_sessions_route(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=100),
):
    return list_user_chat_sessions(user=user, page=page, page_size=page_size)


@router.get("/session")
def user_get_session_route(
    user: CurrentUser,
    session_id: str = Query(..., description="Chat session id"),
):
    return get_user_chat_session_messages(user=user, session_id=session_id)


@router.post("/upload")
async def user_upload_route(
    user: CurrentUser,
    file: UploadFile = File(..., description="PDF, DOCX, JPG, JPEG, or PNG"),
    session_id: str | None = Form(
        None,
        description="Optional chat session id to attach document metadata",
    ),
):
    return await upload_user_file(user=user, file=file, session_id=session_id)


@router.post("/chat")
def user_chat_route(
    user: CurrentUser,
    request: Request,
    payload: UserChatRequest = Body(...),
):
    ref = payload.reference
    fields = payload.field_weights.fields if payload.field_weights else None
    return admin_doc_retrieval(
        user=user,
        request=request,
        query=payload.query,
        session_id=payload.session_id,
        candidate_size=payload.candidate_size,
        similarity_threshold=payload.similarity_threshold,
        final_size=payload.final_size,
        keyword_weight=payload.keyword_weight,
        field_weights=fields,
        topic_ids=ref.topic_ids if ref else None,
        subject_ids=ref.subject_ids if ref else None,
        doc_ids=ref.doc_ids if ref else None,
    )
