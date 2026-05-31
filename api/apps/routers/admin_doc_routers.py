from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.apps.controllers.doc_controller import admin_upload_hf_dataset
from api.apps.middleware.jwt_auth import CurrentUser

router = APIRouter(prefix="/v1/admin", tags=["admin-doc"])


class AdminDatasetUploadRequest(BaseModel):
    dataset_name: str = Field(
        ...,
        description="Hugging Face dataset id, e.g. tmquan/phapdien-moj-gov-vn",
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
        "articles",
        description="Config khi import (preview=false); mặc định articles",
    )
    offset: int = Field(0, ge=0, description="Start index for batched import")
    limit: int | None = Field(
        None,
        ge=1,
        le=500,
        description="Rows per request when preview=false (default 50, max 500)",
    )


@router.post("/doc/upload")
def admin_doc_upload_from_hf(
    user: CurrentUser,
    payload: AdminDatasetUploadRequest,
):
    return admin_upload_hf_dataset(
        user=user,
        dataset_name=payload.dataset_name,
        config=payload.config,
        offset=payload.offset,
        limit=payload.limit,
        preview=payload.preview,
        samples_per_config=payload.samples_per_config,
    )
