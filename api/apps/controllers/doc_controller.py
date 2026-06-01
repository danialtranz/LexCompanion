import mimetypes
import os
import socket
import tempfile
import threading
import time
import urllib.request
from ipaddress import ip_address, ip_network
from pathlib import Path
from urllib.parse import urlencode, urlparse

from bs4 import BeautifulSoup
from fastapi import HTTPException, Request, UploadFile, status
from typing import Any
from fastapi.responses import Response
from markdownify import markdownify as md
from weasyprint import HTML

from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.apps.services.hf_dataset_service import preview_hf_dataset_all_configs
from api.apps.services.kb_service import KnowledgebaseService
from api.apps.services.chat_service import ChatSessionService
from api.apps.services.retrieval_service import admin_retrieve_and_answer
from api.apps.services.legal_service import (
    LegalArticleService,
    LegalIngestionJobService,
    LegalSubjectService,
    LegalTopicService,
    LegalTreeNodeService,
)
from api.db.models import Document, Knowledgebase, LegalArticle, LegalSubject, LegalTopic, LegalTreeNode, Users
from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio, MINIO_CONFIG
from api.utils.redis_conn import REDIS_CONN
from api.utils.upload_preview import content_hash_xxhash128_hex, thumbnail_jpeg_base64
from api.utils.utils import get_uuid

logger = setup_logging()

_DEFAULT_PRESIGN_SECONDS = 7 * 24 * 3600
_LEX_TASK_STREAM = os.getenv("LEX_TASK_STREAM", "lex:tasks")
CRAWL_MIN_INTERVAL_SECONDS = float(os.getenv("CRAWL_MIN_INTERVAL_SECONDS", "1.5"))
_crawl_guard_lock = threading.Lock()
_host_last_crawl_at: dict[str, float] = {}
_PRIVATE_NETS = [
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("127.0.0.0/8"),
    ip_network("169.254.0.0/16"),
    ip_network("::1/128"),
    ip_network("fc00::/7"),
    ip_network("fe80::/10"),
]


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


def _is_public_host(hostname: str) -> bool:
    host = (hostname or "").strip().strip(".").lower()
    if not host:
        return False
    if host in {"localhost", "localhost.localdomain"}:
        return False

    try:
        ip = ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast)
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False

    for info in infos:
        try:
            resolved = ip_address(info[4][0])
        except Exception:
            return False
        if resolved.is_multicast:
            return False
        if any(resolved in net for net in _PRIVATE_NETS):
            return False
    return True


def _validate_and_normalize_url(raw_url: str) -> tuple[str, str]:
    url = (raw_url or "").strip()
    if len(url) > 2048:
        raise HTTPException(status_code=400, detail="URL is too long.")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http/https URLs are supported.")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL.")
    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=400, detail="URLs containing username/password are not supported."
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Cannot parse hostname from URL.")
    if not _is_public_host(hostname):
        raise HTTPException(
            status_code=400,
            detail="Access to private/internal hosts is denied for security reasons.",
        )
    return url, hostname


def _enforce_crawl_rate_limit(hostname: str) -> None:
    now = time.time()
    with _crawl_guard_lock:
        last_time = _host_last_crawl_at.get(hostname, 0.0)
        wait_seconds = CRAWL_MIN_INTERVAL_SECONDS - (now - last_time)
        if wait_seconds > 0:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests to this host. Retry after about {wait_seconds:.1f}s.",
            )
        _host_last_crawl_at[hostname] = now


def _extract_content1_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select("div.content1")
    if not blocks:
        return ""
    return "\n".join(str(block) for block in blocks)


def _convert_html_to_markdown(filtered_html: str) -> str:
    return md(filtered_html, heading_style="ATX").strip()


def _html_to_pdf_bytes(filtered_html: str, base_url: str | None = None) -> bytes:
    body_html = (filtered_html or "").strip()
    if not body_html:
        body_html = "<p>No content.</p>"

    full_html = f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <style>
      @page {{ size: A4; margin: 20mm; }}
      html, body {{
        font-family: "DejaVu Sans", Arial, sans-serif;
        font-size: 12pt;
        line-height: 1.5;
        color: #111827;
      }}
      img {{
        max-width: 100%;
        height: auto;
      }}
      table {{
        border-collapse: collapse;
        width: 100%;
      }}
      th, td {{
        border: 1px solid #d1d5db;
        padding: 6px;
      }}
    </style>
  </head>
  <body>
    {body_html}
  </body>
</html>
"""
    return HTML(string=full_html, base_url=base_url).write_pdf()


async def upload_document_via_url(
    *,
    user: Users,
    kb_id: str | None,
    url_scraping: str,
    doc_name: str | None,
    request: Request | None = None,
) -> dict:
    try:
        logger.info(f"doc upload_via_url: user_id={user.id} kb_id_param={kb_id!r}")
        kb, err = _resolve_kb(user, kb_id)
        if err:
            return err

        normalized_url, hostname = _validate_and_normalize_url(url_scraping)
        _enforce_crawl_rate_limit(hostname)

        req = urllib.request.Request(
            normalized_url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; LegalAgentBot/1.0; +https://localhost)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            html_bytes = resp.read()
            html = html_bytes.decode("utf-8", errors="ignore")

        filtered_html = _extract_content1_html(html)
        if not filtered_html:
            return {"code": 404, "msg": "Could not find content block div.content1", "data": None}

        markdown_text = _convert_html_to_markdown(filtered_html)
        if not markdown_text:
            return {"code": 422, "msg": "Extracted HTML cannot be converted to markdown", "data": None}

        display_name = ((doc_name or "").strip() or "url_upload")[:255]
        file_id = get_uuid()
        doc_id = get_uuid()
        object_key = f"{kb.id}/{file_id}.pdf"

        pdf_body = _html_to_pdf_bytes(filtered_html, base_url=normalized_url)
        content_hash = content_hash_xxhash128_hex(pdf_body)
        thumb_b64 = thumbnail_jpeg_base64(pdf_body, "pdf")

        minio = LexCompanionMinio()
        put_res = minio.put(kb.tenant_id, object_key, pdf_body)
        if put_res is None:
            logger.error(f"MinIO put failed for URL upload tenant={kb.tenant_id} key={object_key}")
            return {"code": 502, "msg": "Failed to store generated PDF in object storage", "data": None}

        presign_ttl = int(os.getenv("MINIO_PRESIGN_EXPIRES_SECONDS", str(_DEFAULT_PRESIGN_SECONDS)))
        access_url = minio.get_presigned_url(kb.tenant_id, object_key, presign_ttl)

        text_dir = Path(tempfile.gettempdir()) / "legalagent_url_upload_texts"
        text_dir.mkdir(parents=True, exist_ok=True)
        text_path = text_dir / f"{file_id}.txt"
        text_path.write_text(markdown_text, encoding="utf-8")

        file_row = FileService.save(
            id=file_id,
            tenant_id=kb.tenant_id,
            created_by=user.id,
            name=f"{display_name}.pdf",
            location=object_key,
            file_content=filtered_html,
            size=len(pdf_body),
            type="pdf",
            source_type="url_scraping",
        )

        DocumentService.save(
            id=doc_id,
            thumbnail=thumb_b64,
            kb_id=kb.id,
            file_id=file_row.id,
            source_type="url_scraping",
            type="pdf",
            created_by=user.id,
            name=f"{display_name}.pdf",
            location="",
            size=len(pdf_body),
            token_num=0,
            chunk_num=0,
            progress=0.0,
            process_duration=0.0,
            suffix=".pdf",
            content_hash=content_hash,
            run="0",
            status="1",
        )
        logger.info(f"doc upload_via_url ok: doc_id={doc_id} file_id={file_id} kb_id={kb.id}")
        return {
            "code": 201,
            "msg": "URL content uploaded",
            "data": {
                "document_id": doc_id,
                "file_id": file_id,
                "kb_id": kb.id,
                "tenant_id": kb.tenant_id,
                "name": f"{display_name}.pdf",
                "size": len(pdf_body),
                "type": "pdf",
                "suffix": ".pdf",
                "object_key": object_key,
                "location": object_key[:255],
                "access_url": access_url,
                "content_url": _public_content_url(request, doc_id),
                "text_file_path": str(text_path),
                "source_url": normalized_url,
                "content_hash": content_hash,
                "has_thumbnail": thumb_b64 is not None,
                "bucket_mode": "single" if MINIO_CONFIG.get("bucket") else "multi",
                "etag": getattr(put_res, "etag", None),
            },
        }
    except HTTPException as http_err:
        return {"code": http_err.status_code, "msg": str(http_err.detail), "data": None}
    except Exception as e:
        logger.error(f"upload_document_via_url error: {e}")
        return {"code": 500, "msg": str(e), "data": None}


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


def _is_super_admin(user: Users) -> bool:
    return bool(getattr(user, "super_admin", False))


def _legal_tree_topic_to_dict(row: LegalTreeNode) -> dict:
    return {
        "id": row.id,
        "node_id": row.node_id,
        "parent_id": row.parent_id,
        "kind": row.kind,
        "number": row.number,
        "title": row.title,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _legal_topic_detail_to_dict(row: LegalTopic) -> dict:
    return {
        "id": row.id,
        "topic_id": row.topic_id,
        "topic_number": row.topic_number,
        "topic_title_vi": row.topic_title_vi,
        "topic_title_en": row.topic_title_en,
        "topic_note": row.topic_note,
        "article_count": row.article_count,
        "demuc_count": row.demuc_count,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _legal_subject_detail_to_dict(row: LegalSubject) -> dict:
    return {
        "id": row.id,
        "subject_id": row.subject_id,
        "topic_id": row.topic_id,
        "topic_number": row.topic_number,
        "topic_title": row.topic_title,
        "subject_number": row.subject_number,
        "subject_title": row.subject_title,
        "source_url": row.source_url,
        "file_version": row.file_version,
        "fetch_status": row.fetch_status,
        "fetch_error": row.fetch_error,
        "scraped_at": row.scraped_at,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _legal_article_to_dict(row: LegalArticle) -> dict:
    return {
        "id": row.id,
        "subject_id": row.subject_id,
        "topic_id": row.topic_id,
        "topic_number": row.topic_number,
        "topic_title": row.topic_title,
        "subject_number": row.subject_number,
        "subject_title": row.subject_title,
        "article_anchor": row.article_anchor,
        "article_title": row.article_title,
        "chapter_title": row.chapter_title,
        "source_note_text": row.source_note_text,
        "source_links": row.source_links,
        "related_note_text": row.related_note_text,
        "content_text": row.content_text,
        "content_char_len": row.content_char_len,
        "content_word_count": row.content_word_count,
        "source_url": row.source_url,
        "scraped_at": row.scraped_at,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def admin_list_legal_topics(
    *,
    user: Users,
    page: int = 1,
    page_size: int = 5,
) -> dict:
    try:
        logger.info(
            "admin_list_legal_topics: user_id={} page={} page_size={}",
            user.id,
            page,
            page_size,
        )
        if not _is_super_admin(user):
            return {"code": 403, "msg": "Super admin required", "data": None}

        total, rows = LegalTreeNodeService.list_top_level_topics_paginated(page, page_size)
        logger.info("admin_list_legal_topics: total={} returned={}", total, len(rows))
        return {
            "code": 200,
            "msg": "OK",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [_legal_tree_topic_to_dict(r) for r in rows],
            },
        }
    except Exception as e:
        logger.error("admin_list_legal_topics error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}


def admin_get_legal_topic_detail(*, user: Users, topic_id: str) -> dict:
    try:
        logger.info(
            "admin_get_legal_topic_detail: user_id={} topic_id={}",
            user.id,
            topic_id,
        )
        if not _is_super_admin(user):
            return {"code": 403, "msg": "Super admin required", "data": None}

        topic_id = (topic_id or "").strip()
        if not topic_id:
            return {"code": 400, "msg": "topic_id is required", "data": None}

        row = LegalTopicService.get_by_topic_id(topic_id)
        if not row:
            return {"code": 404, "msg": "Topic not found", "data": None}

        logger.info("admin_get_legal_topic_detail: found topic_id={}", topic_id)
        return {
            "code": 200,
            "msg": "OK",
            "data": _legal_topic_detail_to_dict(row),
        }
    except Exception as e:
        logger.error("admin_get_legal_topic_detail error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}


def admin_list_legal_subjects(
    *,
    user: Users,
    topic_id: str,
    page: int = 1,
    page_size: int = 5,
) -> dict:
    try:
        logger.info(
            "admin_list_legal_subjects: user_id={} topic_id={} page={} page_size={}",
            user.id,
            topic_id,
            page,
            page_size,
        )
        if not _is_super_admin(user):
            return {"code": 403, "msg": "Super admin required", "data": None}

        topic_id = (topic_id or "").strip()
        if not topic_id:
            return {"code": 400, "msg": "topic_id is required", "data": None}

        total, rows = LegalTreeNodeService.list_subjects_by_topic_paginated(
            topic_id, page, page_size
        )
        logger.info(
            "admin_list_legal_subjects: topic_id={} total={} returned={}",
            topic_id,
            total,
            len(rows),
        )
        return {
            "code": 200,
            "msg": "OK",
            "data": {
                "topic_id": topic_id,
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [_legal_tree_topic_to_dict(r) for r in rows],
            },
        }
    except Exception as e:
        logger.error("admin_list_legal_subjects error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}


def admin_get_legal_subject_detail(*, user: Users, subject_id: str) -> dict:
    try:
        logger.info(
            "admin_get_legal_subject_detail: user_id={} subject_id={}",
            user.id,
            subject_id,
        )
        if not _is_super_admin(user):
            return {"code": 403, "msg": "Super admin required", "data": None}

        subject_id = (subject_id or "").strip()
        if not subject_id:
            return {"code": 400, "msg": "subject_id is required", "data": None}

        row = LegalSubjectService.get_by_subject_id(subject_id)
        if not row:
            return {"code": 404, "msg": "Subject not found", "data": None}

        logger.info("admin_get_legal_subject_detail: found subject_id={}", subject_id)
        return {
            "code": 200,
            "msg": "OK",
            "data": _legal_subject_detail_to_dict(row),
        }
    except Exception as e:
        logger.error("admin_get_legal_subject_detail error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}


def admin_list_legal_articles(
    *,
    user: Users,
    subject_id: str,
    page: int = 1,
    page_size: int = 5,
) -> dict:
    try:
        logger.info(
            "admin_list_legal_articles: user_id={} subject_id={} page={} page_size={}",
            user.id,
            subject_id,
            page,
            page_size,
        )
        if not _is_super_admin(user):
            return {"code": 403, "msg": "Super admin required", "data": None}

        subject_id = (subject_id or "").strip()
        if not subject_id:
            return {"code": 400, "msg": "subject_id is required", "data": None}

        total, rows = LegalArticleService.list_by_subject_paginated(
            subject_id, page, page_size
        )
        logger.info(
            "admin_list_legal_articles: subject_id={} total={} returned={}",
            subject_id,
            total,
            len(rows),
        )
        return {
            "code": 200,
            "msg": "OK",
            "data": {
                "subject_id": subject_id,
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [_legal_article_to_dict(r) for r in rows],
            },
        }
    except Exception as e:
        logger.error("admin_list_legal_articles error: {}", e)
        return {"code": 500, "msg": str(e), "data": None}


def admin_upload_hf_dataset(
    *,
    user: Users,
    dataset_name: str,
    dataset_version: str,
    config: str | None = None,
    offset: int = 0,
    limit: int | None = None,
    preview: bool = False,
    samples_per_config: int | None = None,
) -> dict:
    """
    Super admin: preview toàn bộ config HF, hoặc import một config vào KB/MinIO/ES.
    """
    try:
        logger.info(
            f"admin hf upload: user_id={user.id} dataset={dataset_name!r} "
            f"preview={preview} offset={offset}"
        )
        if not _is_super_admin(user):
            return {"code": 403, "msg": "Super admin required", "data": None}

        dataset_name = (dataset_name or "").strip()
        if not dataset_name or "/" not in dataset_name:
            return {
                "code": 400,
                "msg": "dataset_name must be a Hugging Face repo id (e.g. org/name)",
                "data": None,
            }

        if preview:
            per_cfg = samples_per_config if samples_per_config is not None else int(
                os.getenv("HF_PREVIEW_SAMPLES_PER_CONFIG", "20")
            )
            result = preview_hf_dataset_all_configs(
                dataset_name=dataset_name,
                samples_per_config=per_cfg,
            )
            logger.info(
                f"admin hf preview done: configs={result['config_count']} "
                f"samples_per_config={per_cfg}"
            )
            return {
                "code": 200,
                "msg": "Hugging Face dataset preview (all configs)",
                "data": result,
            }

        cfg = (config or "all").strip().lower() or "all"
        if cfg != "all":
            return {
                "code": 400,
                "msg": "Only config=all is supported for import (full dataset to PostgreSQL)",
                "data": None,
            }

        if not REDIS_CONN.is_alive() or REDIS_CONN.REDIS is None:
            logger.warning(f"admin hf upload: redis unavailable dataset={dataset_name!r}")
            return {"code": 503, "msg": "Task queue unavailable", "data": None}

        dataset_version = (dataset_version or "").strip()
        if not dataset_version:
            return {"code": 400, "msg": "dataset_version is required", "data": None}

        running_job = LegalIngestionJobService.get_running_job(
            dataset_name, dataset_version
        )
        if running_job:
            logger.info(
                f"admin hf upload blocked: running job_id={running_job.id} "
                f"dataset={dataset_name!r} version={dataset_version!r}"
            )
            return {
                "code": 409,
                "msg": "Import already running for this dataset and version",
                "data": {
                    "job_id": running_job.id,
                    "dataset_name": dataset_name,
                    "dataset_version": dataset_version,
                    "status": running_job.status,
                },
            }

        latest_completed = LegalIngestionJobService.get_latest_completed_job(dataset_name)
        if latest_completed and (latest_completed.dataset_version or "") == dataset_version:
            logger.info(
                f"admin hf upload blocked: already imported job_id={latest_completed.id} "
                f"dataset={dataset_name!r} version={dataset_version!r}"
            )
            return {
                "code": 409,
                "msg": "This dataset version was already imported",
                "data": {
                    "job_id": latest_completed.id,
                    "dataset_name": dataset_name,
                    "dataset_version": dataset_version,
                    "status": latest_completed.status,
                    "finished_at": (
                        latest_completed.finished_at.isoformat()
                        if latest_completed.finished_at
                        else None
                    ),
                },
            }

        job = LegalIngestionJobService.create_running(
            dataset_name=dataset_name,
            dataset_version=dataset_version,
        )
        payload = {
            "type": "import_hf_phapdien",
            "job_id": job.id,
            "dataset_name": dataset_name,
            "dataset_version": dataset_version,
        }
        ok = REDIS_CONN.queue_product(_LEX_TASK_STREAM, payload)
        if not ok:
            LegalIngestionJobService.mark_finished(
                job.id,
                status="failed",
                error_message="Failed to enqueue import task",
            )
            logger.error(f"admin hf upload: queue_product failed job_id={job.id}")
            return {"code": 502, "msg": "Failed to enqueue import task", "data": None}

        logger.info(f"admin hf upload enqueued job_id={job.id} dataset={dataset_name!r}")
        return {"code": 0, "msg": "running", "data": None}
    except Exception as e:
        logger.error(f"admin_upload_hf_dataset error: {e}")
        return {"code": 500, "msg": str(e), "data": None}


def admin_doc_retrieval(
    *,
    user: Users,
    request: Request,
    query: str,
    session_id: str | None = None,
    candidate_size: int = 100,
    similarity_threshold: float = 0.5,
    final_size: int = 5,
    keyword_weight: float = 0.3,
    field_weights: list[str] | None = None,
    topic_ids: list[str] | None = None,
    subject_ids: list[str] | None = None,
    doc_ids: list[str] | None = None,
) -> dict:
    try:
        logger.info(
            "admin_doc_retrieval: user_id={} candidate_size={} threshold={} final_size={} query={}",
            user.id,
            candidate_size,
            similarity_threshold,
            final_size,
            query,
        )
        if not _is_super_admin(user):
            return {"code": 403, "msg": "Super admin required", "data": None}

        query = (query or "").strip()
        if not query:
            return {"code": 400, "msg": "query is required", "data": None}

        persist_session_id = (session_id or "").strip() or None

        reranker = getattr(request.app.state, "reranker", None)
        payload: dict[str, Any] = admin_retrieve_and_answer(
            query=query,
            session_id=persist_session_id,
            user_id=user.id,
            candidate_size=candidate_size,
            similarity_threshold=similarity_threshold,
            final_size=final_size,
            keyword_weight=keyword_weight,
            field_weights=field_weights,
            topic_ids=topic_ids or None,
            subject_ids=subject_ids or None,
            extra_doc_ids=doc_ids or None,
            reranker=reranker,
        )
        if not payload.get("answer"):
            return {
                "code": 502,
                "msg": "LLM did not return an answer",
                "data": payload,
            }

        logger.info(
            "admin_doc_retrieval: references={}",
            len(payload.get("reference") or []),
        )

        if persist_session_id:
            try:
                ChatSessionService.save_retrieval_exchange(
                    session_id=persist_session_id,
                    user=user,
                    query=query,
                    answer=payload["answer"],
                    references=payload.get("reference"),
                )
            except PermissionError as e:
                logger.warning("admin_doc_retrieval session denied: {}", e)
                return {"code": 403, "msg": str(e), "data": None}

        return {"code": 200, "msg": "OK", "data": payload}
    except PermissionError as e:
        logger.warning("admin_doc_retrieval session denied: {}", e)
        return {"code": 403, "msg": str(e), "data": None}
    except ValueError as e:
        logger.error("admin_doc_retrieval validation error: {}", e)
        return {"code": 400, "msg": str(e), "data": None}
    except Exception as e:
        logger.error("admin_doc_retrieval error: {}", e)
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
