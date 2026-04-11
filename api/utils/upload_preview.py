"""Thumbnail (JPEG base64) và xxhash128 hex (tối đa 36 ký tự) cho file upload."""

from __future__ import annotations

import base64
import io
import logging

import xxhash

logger = logging.getLogger(__name__)

# xxhash128 hex = 32 ký tự; model cho phép tối đa 36
MAX_CONTENT_HASH_LEN = 36
_THUMB_MAX_EDGE = 256


def content_hash_xxhash128_hex(body: bytes) -> str:
    """Hash nội dung file bằng xxhash128, biểu diễn hex, cắt tối đa 36 ký tự."""
    s = xxhash.xxh128(body).hexdigest()
    return s[:MAX_CONTENT_HASH_LEN]


def thumbnail_jpeg_base64(body: bytes, ext_type: str) -> str | None:
    """
    Trả về chuỗi base64 của JPEG thu nhỏ, hoặc None nếu không hỗ trợ / lỗi.
    Hỗ trợ: jpeg/png/gif/webp/bmp/tiff và PDF (trang đầu).
    """
    ext = (ext_type or "").lower().lstrip(".")
    try:
        if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "tif", "tiff"):
            return _thumbnail_from_image(body)
        if ext == "pdf":
            return _thumbnail_from_pdf(body)
    except Exception:
        logger.exception("thumbnail_jpeg_base64 failed ext=%s", ext)
    return None


def _thumbnail_from_image(body: bytes) -> str:
    from PIL import Image

    im = Image.open(io.BytesIO(body))
    im.thumbnail((_THUMB_MAX_EDGE, _THUMB_MAX_EDGE), Image.Resampling.LANCZOS)
    if im.mode in ("RGBA", "P"):
        im = im.convert("RGB")
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=82, optimize=True)
    return base64.b64encode(out.getvalue()).decode("ascii")


def _thumbnail_from_pdf(body: bytes) -> str:
    import fitz
    from PIL import Image

    with fitz.open(stream=body, filetype="pdf") as doc:
        page = doc.load_page(0)
        w = page.rect.width
        scale = min(1.0, float(_THUMB_MAX_EDGE) / max(w, 1.0))
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        png_bytes = pix.tobytes("png")

    im = Image.open(io.BytesIO(png_bytes))
    im.thumbnail((_THUMB_MAX_EDGE, _THUMB_MAX_EDGE), Image.Resampling.LANCZOS)
    if im.mode in ("RGBA", "P"):
        im = im.convert("RGB")
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=82, optimize=True)
    return base64.b64encode(out.getvalue()).decode("ascii")
