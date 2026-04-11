import mimetypes
import os
from pathlib import Path
from urllib.parse import urlencode

from fastapi import HTTPException, Request, UploadFile, status
from fastapi.responses import Response

from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.apps.services.kb_service import KnowledgebaseService
from api.db.models import Document, Knowledgebase, Users
from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio, MINIO_CONFIG
from api.utils.redis_conn import REDIS_CONN
from api.utils.upload_preview import content_hash_xxhash128_hex, thumbnail_jpeg_base64
from api.utils.utils import get_uuid

logger = setup_logging()

_DEFAULT_PRESIGN_SECONDS = 7 * 24 * 3600
_LEX_TASK_STREAM = os.getenv("LEX_TASK_STREAM", "lex:tasks")


def _public_content_url(request: Request | None, doc_id: str) -> str:
    """URL API stream file (JWT); client dùng fetch + blob."""
    q = urlencode({"doc_id": doc_id})
    if request is not None:
        base = str(request.base_url).rstrip("/")
        return f"{base}/v1/doc/content?{q}"
    base = os.getenv("API_PUBLIC_BASE", "").rstrip("/")
    if base:
        return f"{base}/v1/doc/content?{q}"
    return f"/v1/doc/content?{q}"


def _normalize_kb_id(kb_id: str | None) -> str | None:
    if kb_id is None:
        return None
    s = str(kb_id).strip()
    if s.lower() in ("", "null", "undefined", "none"):
        return None
    return s


def _resolve_kb(user: Users, kb_id: str | None) -> tuple[Knowledgebase | None, dict | None]:
    """Giống upload: kb_id null → resolve_kb_for_me_upload; có kb_id → get theo id."""
    kb_key = _normalize_kb_id(kb_id)
    if kb_key is None:
        kb = KnowledgebaseService.resolve_kb_for_me_upload(user.id)
        if not kb:
            return None, {
                "code": 404,
                "msg": "No knowledge base with permission=me for your account",
                "data": None,
            }
        return kb, None
    kb = KnowledgebaseService.get_or_none(id=kb_key)
    if not kb:
        return None, {"code": 404, "msg": "Knowledge base not found", "data": None}
    return kb, None


def _document_to_dict(doc: Document, *, include_thumbnail: bool = False) -> dict:
    """Chuẩn hóa document ra JSON (mặc định không trả thumbnail dài)."""
    out = {
        "id": doc.id,
        "kb_id": doc.kb_id,
        "file_id": doc.file_id,
        "name": doc.name,
        "type": doc.type,
        "suffix": doc.suffix,
        "size": doc.size,
        "token_num": doc.token_num,
        "chunk_num": doc.chunk_num,
        "progress": doc.progress,
        "process_duration": doc.process_duration,
        "content_hash": doc.content_hash,
        "source_type": doc.source_type,
        "location": doc.location,
        "created_by": doc.created_by,
        "run": doc.run,
        "status": doc.status,
        "create_date": doc.create_date.isoformat() if doc.create_date else None,
        "update_date": doc.update_date.isoformat() if doc.update_date else None,
    }
    if include_thumbnail:
        out["thumbnail"] = doc.thumbnail
    else:
        out["has_thumbnail"] = bool(doc.thumbnail)
    return out


def _parse_file_meta(original_name: str | None) -> tuple[str, str, str]:
    """display_name, type (no dot), suffix (with dot, max 36)."""
    raw = (original_name or "").strip() or "upload"
    base = os.path.basename(raw)
    suf = Path(base).suffix.lower()
    if not suf or len(suf) > 36:
        suf = ".bin"
    ext = suf[1:] if len(suf) > 1 else "bin"
    if len(ext) > 36:
        ext = ext[:36]
    name = base[:255] if len(base) <= 255 else base[:252] + "..."
    return name, ext, suf[:36]


async def upload_document(
    *, user: Users, file: UploadFile, kb_id: str | None, request: Request | None = None
) -> dict:
    try:
        logger.info(f"doc upload: user_id={user.id} kb_id_param={kb_id!r}")
        kb, err = _resolve_kb(user, kb_id)
        if err:
            return err

        body = await file.read()
        if not body:
            return {"code": 400, "msg": "Empty file", "data": None}

        display_name, ext_type, suffix = _parse_file_meta(file.filename)
        file_id = get_uuid()
        object_key = f"{kb.id}/{file_id}{suffix}"

        content_hash = content_hash_xxhash128_hex(body)
        thumb_b64 = thumbnail_jpeg_base64(body, ext_type)

        minio = LexCompanionMinio()
        # Logical bucket theo tenant của KB (prefix trong single-bucket mode)
        put_res = minio.put(kb.tenant_id, object_key, body)
        if put_res is None:
            logger.error(f"MinIO put failed tenant={kb.tenant_id} key={object_key}")
            return {"code": 502, "msg": "Failed to store file in object storage", "data": None}

        presign_ttl = int(os.getenv("MINIO_PRESIGN_EXPIRES_SECONDS", str(_DEFAULT_PRESIGN_SECONDS)))
        access_url = minio.get_presigned_url(kb.tenant_id, object_key, presign_ttl)
        # location: đường dẫn object ổn định (<=255); URL tạm thời trả trong data
        location_key = object_key
        if len(location_key) > 255:
            location_key = location_key[:255]

        etag = getattr(put_res, "etag", None)

        file_row = FileService.save(
            id=file_id,
            tenant_id=kb.tenant_id,
            created_by=user.id,
            name=display_name,
            location=location_key,
            size=len(body),
            type=ext_type[:36],
            source_type="minio",
        )

        doc_id = get_uuid()
        DocumentService.save(
            id=doc_id,
            thumbnail=thumb_b64,
            kb_id=kb.id,
            file_id=file_row.id,
            source_type="minio",
            type=ext_type[:36],
            created_by=user.id,
            name=display_name,
            location="",
            size=len(body),
            token_num=0,
            chunk_num=0,
            progress=0.0,
            process_duration=0.0,
            suffix=suffix[:36],
            content_hash=content_hash,
            run="0",
            status="1",
        )

        logger.info(f"doc upload ok: doc_id={doc_id} file_id={file_id} kb_id={kb.id}")

        return {
            "code": 201,
            "msg": "File uploaded",
            "data": {
                "document_id": doc_id,
                "file_id": file_id,
                "kb_id": kb.id,
                "tenant_id": kb.tenant_id,
                "name": display_name,
                "size": len(body),
                "type": ext_type,
                "suffix": suffix,
                "object_key": object_key,
                "location": location_key,
                "access_url": access_url,
                "content_url": _public_content_url(request, doc_id),
                "etag": etag,
                "bucket_mode": "single" if MINIO_CONFIG.get("bucket") else "multi",
                "content_hash": content_hash,
                "has_thumbnail": thumb_b64 is not None,
            },
        }
    except Exception as e:
        logger.error(f"upload_document error: {e}")
        return {"code": 500, "msg": str(e), "data": None}


def list_documents(
    *,
    user: Users,
    kb_id: str | None,
    page: int = 1,
    page_size: int = 5,
) -> dict:
    try:
        kb, err = _resolve_kb(user, kb_id)
        if err:
            return err
        total, rows = DocumentService.list_active_by_kb_id(kb.id, page, page_size)
        logger.info(f"list_documents: kb_id={kb.id} total={total} page={page}")
        return {
            "code": 0,
            "msg": "OK",
            "data": {
                "kb_id": kb.id,
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [_document_to_dict(d, include_thumbnail=False) for d in rows],
            },
        }
    except Exception as e:
        logger.error(f"list_documents error: {e}")
        return {"code": 500, "msg": str(e), "data": None}


def get_document_access_url(*, user: Users, doc_id: str, request: Request | None = None) -> dict:
    try:
        doc = DocumentService.get_active_by_id_and_owner(doc_id, user.id)
        if not doc:
            return {"code": 404, "msg": "Document not found", "data": None}
        if not doc.file_id:
            return {"code": 404, "msg": "Document has no file", "data": None}

        file_row = FileService.get_or_none(id=doc.file_id)
        if not file_row or not file_row.location:
            return {"code": 404, "msg": "File record or object key missing", "data": None}

        presign_ttl = int(os.getenv("MINIO_PRESIGN_EXPIRES_SECONDS", str(_DEFAULT_PRESIGN_SECONDS)))
        minio = LexCompanionMinio()
        access_url = minio.get_presigned_url(file_row.tenant_id, file_row.location, presign_ttl)
        if not access_url:
            return {"code": 502, "msg": "Could not generate presigned URL", "data": None}
        logger.info(f"get_document_access_url: doc_id={doc_id}")
        return {
            "code": 0,
            "msg": "OK",
            "data": {
                "document_id": doc.id,
                "file_id": file_row.id,
                "access_url": access_url,
                "content_url": _public_content_url(request, doc.id),
                "expires_in_seconds": presign_ttl,
                "object_key": file_row.location,
                "tenant_id": file_row.tenant_id,
            },
        }
    except Exception as e:
        logger.error(f"get_document_access_url error: {e}")
        return {"code": 500, "msg": str(e), "data": None}


def stream_document_content(*, user: Users, doc_id: str) -> Response:
    """
    Đọc object từ MinIO và trả raw bytes cho client (fetch -> blob).
    Cùng quyền với get_document_access_url (chỉ owner).
    """
    doc = DocumentService.get_active_by_id_and_owner(doc_id, user.id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not doc.file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document has no file")

    file_row = FileService.get_or_none(id=doc.file_id)
    if not file_row or not file_row.location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File record or object key missing",
        )

    minio = LexCompanionMinio()
    data = minio.get(file_row.tenant_id, file_row.location)
    if data is None:
        logger.error(f"MinIO get empty: tenant={file_row.tenant_id} key={file_row.location}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to read file from object storage",
        )

    raw_name = (doc.name or "").strip()
    suf = (doc.suffix or "").strip()
    if raw_name:
        filename = raw_name
    elif suf:
        filename = f"file{suf}" if suf.startswith(".") else f"file.{suf}"
    else:
        filename = "file"

    media_type, _ = mimetypes.guess_type(filename)
    if not media_type:
        media_type = "application/octet-stream"

    safe_name = filename.replace('"', "'")
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


def run_document_parse(
    *,
    user: Users,
    doc_id: str,
    parse_type: str = "docdealing",
) -> dict:
    """
    Đưa document vào Redis queue để worker parse/embedding.

    Chỉ document còn hiệu lực: trong DB ``status='1'`` (đã xóa mềm là ``status='0'``, không được parse).

    - ``progress >= 1`` → đã parse, không enqueue.
    - ``progress < 1`` (gồm 0 hoặc đang xử lý dở) → đẩy task vào Redis queue.
    """
    try:
        doc = DocumentService.get_active_by_id_and_owner(doc_id, user.id)
        if not doc:
            logger.info(f"run_document_parse: not found or not active doc_id={doc_id}")
            return {"code": 404, "msg": "Document not found", "data": None}

        if float(doc.progress) >= 1.0:
            logger.info(
                f"run_document_parse: already parsed doc_id={doc_id} progress={doc.progress}"
            )
            return {
                "code": 409,
                "msg": "Document already parsed",
                "data": {
                    "document_id": doc.id,
                    "progress": doc.progress,
                },
            }

        if not doc.file_id:
            return {"code": 400, "msg": "Document has no file", "data": None}

        if not REDIS_CONN.is_alive() or REDIS_CONN.REDIS is None:
            logger.warning(f"run_document_parse: redis unavailable doc_id={doc_id}")
            return {"code": 503, "msg": "Task queue unavailable", "data": None}

        payload = {
            "type": "parse_document",
            "document_id": doc.id,
            "parse_type": (parse_type or "docdealing").strip() or "docdealing",
        }
        ok = REDIS_CONN.queue_product(_LEX_TASK_STREAM, payload)
        if not ok:
            logger.error(f"run_document_parse: queue_product failed doc_id={doc_id}")
            return {"code": 502, "msg": "Failed to enqueue parse task", "data": None}

        DocumentService.mark_parse_queued(doc.id)
        logger.info(
            f"run_document_parse: enqueued doc_id={doc.id} parse_type={payload['parse_type']}"
        )
        return {
            "code": 0,
            "msg": "Parse task queued",
            "data": {
                "document_id": doc.id,
                "parse_type": payload["parse_type"],
                "stream": _LEX_TASK_STREAM,
            },
        }
    except Exception as e:
        logger.error(f"run_document_parse error: {e}")
        return {"code": 500, "msg": str(e), "data": None}


def delete_document(*, user: Users, doc_id: str) -> dict:
    try:
        doc = DocumentService.get_or_none(id=doc_id)
        if not doc:
            return {"code": 404, "msg": "Document not found", "data": None}
        if doc.created_by != user.id:
            return {"code": 403, "msg": "Forbidden", "data": None}
        if doc.status != "1":
            return {"code": 409, "msg": "Document already removed", "data": None}

        DocumentService.update_by_id(doc_id, {"status": "0"})
        updated = DocumentService.get_or_none(id=doc_id)
        logger.info(f"delete_document soft: doc_id={doc_id}")
        return {
            "code": 0,
            "msg": "Document deleted",
            "data": _document_to_dict(updated, include_thumbnail=True) if updated else None,
        }
    except Exception as e:
        logger.error(f"delete_document error: {e}")
        return {"code": 500, "msg": str(e), "data": None}
