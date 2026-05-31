from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from api.apps.controllers.doc_controller import (
    admin_get_legal_subject_detail,
    admin_get_legal_topic_detail,
    admin_list_legal_articles,
    admin_list_legal_subjects,
    admin_list_legal_topics,
    admin_upload_hf_dataset,
)
from api.apps.middleware.jwt_auth import CurrentUser

router = APIRouter(prefix="/v1/admin", tags=["admin-doc"])


class AdminDatasetUploadRequest(BaseModel):
    dataset_name: str = Field(
        ...,
        description="Hugging Face dataset id, e.g. tmquan/phapdien-moj-gov-vn",
    )
    dataset_version: str = Field(
        ...,
        description="Phiên bản dataset (lưu vào legal_ingestion_jobs.dataset_version)",
    )
    preview: bool = Field(
        False,
        description=(
            "true: tải mẫu cả 6 config (articles, subjects, tree_nodes, "
            "ontology_*), không ghi DB/ES"
        ),
    )
    samples_per_config: int | None = Field(
        20,
        ge=1,
        le=100,
        description="Số dòng mẫu mỗi config khi preview=true (mặc định 20)",
    )
    config: str | None = Field(
        "all",
        description="Import config; only 'all' is supported (full dataset → PostgreSQL via queue)",
    )
    offset: int = Field(0, ge=0, description="Start index for batched import")
    limit: int | None = Field(
        None,
        ge=1,
        le=500,
        description="Rows per request when preview=false (default 50, max 500)",
    )


@router.get("/doc/topic")
def admin_doc_list_topics(
    user: CurrentUser,
    topic_id: str | None = Query(None, description="Topic id; nếu có thì trả detail thay vì list"),
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=100),
):
    if topic_id:
        return admin_get_legal_topic_detail(user=user, topic_id=topic_id)
    return admin_list_legal_topics(user=user, page=page, page_size=page_size)


@router.get("/doc/subject")
def admin_doc_list_subjects(
    user: CurrentUser,
    subject_id: str | None = Query(None, description="Subject id; nếu có thì trả detail"),
    topic_id: str | None = Query(None, description="Topic node_id (parent của subject)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=100),
):
    if subject_id:
        return admin_get_legal_subject_detail(user=user, subject_id=subject_id)
    return admin_list_legal_subjects(
        user=user,
        topic_id=topic_id or "",
        page=page,
        page_size=page_size,
    )


@router.get("/doc/articles")
def admin_doc_list_articles(
    user: CurrentUser,
    subject_id: str = Query(..., description="Subject id để lọc articles"),
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=100),
):
    return admin_list_legal_articles(
        user=user,
        subject_id=subject_id,
        page=page,
        page_size=page_size,
    )


@router.post("/doc/upload")
def admin_doc_upload_from_hf(
    user: CurrentUser,
    payload: AdminDatasetUploadRequest,
):
    return admin_upload_hf_dataset(
        user=user,
        dataset_name=payload.dataset_name,
        dataset_version=payload.dataset_version,
        config=payload.config,
        offset=payload.offset,
        limit=payload.limit,
        preview=payload.preview,
        samples_per_config=payload.samples_per_config,
    )
