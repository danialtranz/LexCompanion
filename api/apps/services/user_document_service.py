"""User chat file upload: MinIO → DB → DocDealing → ES user_documents."""

from __future__ import annotations

import os
from typing import Any

from fastapi import UploadFile

from api.apps.services.chat_service import ChatSessionService
from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.apps.services.kb_service import KnowledgebaseService
from api.db.models import Users, Knowledgebase
from api.utils.elastic_user_documents_index import index_user_document_chunks
from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio
from api.utils.token_count import (
    count_tokens,
    retrieval_strategy_for_token_count,
)
from api.utils.upload_preview import content_hash_xxhash128_hex, thumbnail_jpeg_base64
from api.utils.utils import get_uuid
from deepagent.core.document_loaders.docdealing import DocDealingLoader, SUPPORTED_SUFFIXES
from deepagent.core.text_splitters.user_document_split import UserDocumentSplitter

logger = setup_logging()

_DEFAULT_PRESIGN_SECONDS = 7 * 24 * 3600


def _normalize_session_id(session_id: str | None) -> str | None:
    if session_id is None:
        return None
    s = str(session_id).strip().strip('"').strip("'")
    if s.lower() in ("", "null", "undefined", "none"):
        return None
    return s


def _parse_file_meta(original_name: str | None) -> tuple[str, str, str]:
    from pathlib import Path

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


def _attach_document_to_session(
    *,
    session_id: str,
    user: Users,
    document_id: str,
    file_id: str,
    name: str,
    doc_type: str,
    chunk_count: int,
    token_count: int,
) -> None:
    session = ChatSessionService.get_session(session_id)
    if not session:
        raise LookupError("Session not found")
    if session.user_id != user.id:
        raise PermissionError("Session does not belong to this user")
    if session.status == "deleted":
        raise LookupError("Session not found")

    meta: dict[str, Any] = dict(session.metadata or {})
    uploads = list(meta.get("uploads") or [])
    entry = {
        "document_id": document_id,
        "file_id": file_id,
        "name": name,
        "doc_type": doc_type,
        "chunk_count": chunk_count,
        "token_count": token_count,
    }
    uploads.append(entry)
    meta["uploads"] = uploads
    doc_ids = list(meta.get("document_ids") or [])
    if document_id not in doc_ids:
        doc_ids.append(document_id)
    meta["document_ids"] = doc_ids

    total_tokens = sum(int(u.get("token_count") or 0) for u in uploads)
    meta["total_token_count"] = total_tokens
    meta["retrieval_strategy"] = retrieval_strategy_for_token_count(total_tokens)

    session.metadata = meta
    session.save()
    logger.info(
        "session metadata updated session_id={} document_id={} tokens={} strategy={}",
        session_id,
        document_id,
        total_tokens,
        meta["retrieval_strategy"],
    )


async def process_user_file_upload(
    *,
    user: Users,
    file: UploadFile,
    session_id: str | None = None,
) -> dict:
    sid = _normalize_session_id(session_id)
    if sid:
        session = ChatSessionService.get_session(sid)
        if not session:
            return {"code": 404, "msg": "Session not found", "data": None}
        if session.user_id != user.id:
            return {"code": 403, "msg": "Session does not belong to this user", "data": None}
        if session.status == "deleted":
            return {"code": 404, "msg": "Session not found", "data": None}

    kb = KnowledgebaseService.resolve_kb_for_me_upload(user.id)
    ## tao fake 1 row kb va lu vao luon trong db
    kb=None
    if not kb:
        kb = KnowledgebaseService.save(
        id=get_uuid(),
        name="Fake KB",
        tenant_id=user.id,
        created_by=user.id,
        status="1",
        language="vietnamese",
        permission="me",
        similarity_threshold=0.2,
        vector_size=1024,
        doc_num=0,
        token_num=0,
        chunk_num=0,
        description="Fake KB",
    )
        # return {
        #     "code": 404,
        #     "msg": "No knowledge base with permission=me for your account",
        #     "data": None,
        # }

    body = await file.read()
    if not body:
        return {"code": 400, "msg": "Empty file", "data": None}

    display_name, ext_type, suffix = _parse_file_meta(file.filename)
    if not DocDealingLoader.is_supported_suffix(suffix):
        allowed = ", ".join(sorted(SUPPORTED_SUFFIXES))
        return {
            "code": 400,
            "msg": f"Unsupported file type. Allowed: {allowed}",
            "data": None,
        }

    file_id = get_uuid()
    doc_id = get_uuid()
    object_key = f"{kb.id}/{file_id}{suffix}"

    content_hash = content_hash_xxhash128_hex(body)
    thumb_b64 = thumbnail_jpeg_base64(body, ext_type)

    minio = LexCompanionMinio()
    put_res = minio.put(kb.tenant_id, object_key, body)
    if put_res is None:
        logger.error("MinIO put failed tenant={} key={}", kb.tenant_id, object_key)
        return {"code": 502, "msg": "Failed to store file in object storage", "data": None}

    location_key = object_key[:255] if len(object_key) > 255 else object_key

    file_row = FileService.save(
        id=file_id,
        tenant_id=kb.tenant_id,
        created_by=user.id,
        name=display_name,
        location=location_key,
        size=len(body),
        type=ext_type[:36],
        source_type="user_upload",
    )

    DocumentService.save(
        id=doc_id,
        thumbnail=thumb_b64,
        kb_id=kb.id,
        file_id=file_row.id,
        source_type="user_upload",
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

    try:
        parsed_text = DocDealingLoader.parse_bytes(body, suffix=suffix)
    except Exception as e:
        logger.error("DocDealing parse failed doc_id={}: {}", doc_id, e)
        DocumentService.update_by_id(
            doc_id, {"status": "0", "progress": -1.0}
        )
        return {"code": 422, "msg": f"Failed to parse file: {e}", "data": None}

    splitter = UserDocumentSplitter()
    chunks = splitter.split_with_metadata(parsed_text, document_id=doc_id)
    token_count = count_tokens(parsed_text)
    if token_count < 1 and parsed_text.strip():
        token_count = 1

    try:
        indexed = index_user_document_chunks(
            user_id=user.id,
            kb_id=kb.id,
            document_id=doc_id,
            doc_title=display_name,
            doc_type=ext_type,
            chunks=chunks,
        )
    except Exception as e:
        logger.error("ES index user_documents failed doc_id={}: {}", doc_id, e)
        DocumentService.update_by_id(
            doc_id, {"status": "0", "progress": -1.0}
        )
        return {"code": 502, "msg": f"Failed to index document chunks: {e}", "data": None}

    DocumentService.update_by_id(
        doc_id,
        {
            "chunk_num": indexed,
            "token_num": token_count,
            "progress": 1.0,
        },
    )

    if sid:
        try:
            _attach_document_to_session(
                session_id=sid,
                user=user,
                document_id=doc_id,
                file_id=file_id,
                name=display_name,
                doc_type=ext_type,
                chunk_count=indexed,
                token_count=token_count,
            )
        except PermissionError as e:
            return {"code": 403, "msg": str(e), "data": None}
        except LookupError as e:
            return {"code": 404, "msg": str(e), "data": None}

    presign_ttl = int(
        os.getenv("MINIO_PRESIGN_EXPIRES_SECONDS", str(_DEFAULT_PRESIGN_SECONDS))
    )
    access_url = minio.get_presigned_url(kb.tenant_id, object_key, presign_ttl)

    return {
        "code": 201,
        "msg": "File uploaded and indexed",
        "data": {
            "document_id": doc_id,
            "file_id": file_id,
            "kb_id": kb.id,
            "session_id": sid,
            "name": display_name,
            "type": ext_type,
            "suffix": suffix,
            "size": len(body),
            "chunk_count": indexed,
            "token_count": token_count,
            "retrieval_strategy": retrieval_strategy_for_token_count(token_count),
            "object_key": object_key,
            "access_url": access_url,
            "content_hash": content_hash,
        },
    }
