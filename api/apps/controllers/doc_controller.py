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
from fastapi.responses import Response
from markdownify import markdownify as md
from weasyprint import HTML

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
