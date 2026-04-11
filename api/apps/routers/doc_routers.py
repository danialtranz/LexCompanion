from fastapi import APIRouter, File, Query, Request, UploadFile

from api.apps.controllers.doc_controller import (
    delete_document,
    get_document_access_url,
    list_documents,
    run_document_parse,
    stream_document_content,
    upload_document,
)
from api.apps.middleware.jwt_auth import CurrentUser

router = APIRouter(prefix="/v1", tags=["doc"])


@router.get("/docs")
def docs_list(
    user: CurrentUser,
    kb_id: str | None = Query(
        None,
        description="Knowledge base id; omit or 'null' to resolve via permission=me (same as upload)",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=100),
):
    return list_documents(user=user, kb_id=kb_id, page=page, page_size=page_size)


@router.post("/doc/upload")
async def doc_upload(
    request: Request,
    user: CurrentUser,
    file: UploadFile = File(..., description="File to upload"),
    kb_id: str | None = Query(
        None,
        description="Knowledge base id; omit or 'null' to use your latest KB (permission=me)",
    ),
):
    return await upload_document(user=user, file=file, kb_id=kb_id, request=request)


@router.get("/doc/content")
def doc_stream_file(
    user: CurrentUser,
    doc_id: str = Query(..., description="Document id"),
):
    """
    Trả nội dung file từ MinIO (body raw). Client: fetch(url, { headers: { Authorization } }).then(r => r.blob()).
    """
    return stream_document_content(user=user, doc_id=doc_id)


@router.get("/doc")
def doc_get_presigned(
    request: Request,
    user: CurrentUser,
    doc_id: str = Query(..., description="Document id"),
):
    return get_document_access_url(user=user, doc_id=doc_id, request=request)


@router.delete("/doc")
def doc_soft_delete(
    user: CurrentUser,
    doc_id: str = Query(..., description="Document id"),
):
    return delete_document(user=user, doc_id=doc_id)


@router.post("/doc/run")
def doc_run_parse(
    user: CurrentUser,
    doc_id: str = Query(..., description="Document id"),
    parse_type: str = Query(
        "docdealing",
        description="Worker pipeline key (e.g. docdealing)",
    ),
):
    """Enqueue parse/embedding task (Redis). Active docs only (status=1); progress>=1 → already parsed."""
    return run_document_parse(user=user, doc_id=doc_id, parse_type=parse_type)
