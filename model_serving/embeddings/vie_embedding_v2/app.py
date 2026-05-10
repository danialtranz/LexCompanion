from __future__ import annotations

from contextlib import asynccontextmanager
import os
import threading
import time
from typing import Any

import jwt
from fastapi import FastAPI
from fastapi import Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

from load_model import get_loaded_model, is_model_loaded, load_model, unload_model

class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ApiResponse(BaseModel):
    code: int
    msg: str
    data: Any | None = None


class OpenAIEmbeddingsRequest(BaseModel):
    """OpenAI-compatible body for ``POST /v1/embeddings`` (LangChain LocalAIEmbeddings)."""

    model_config = ConfigDict(extra="ignore")

    model: str | None = None
    input: str | list[str]


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm up model on server start so requests only do inference.
    load_dotenv()
    load_model()
    try:
        yield
    finally:
        unload_model()


app = FastAPI(title="Vietnamese Embedding v2 Serving", lifespan=lifespan)
_MAX_CONCURRENT = max(1, int(os.getenv("EMBEDDING_MAX_CONCURRENT", "1")))
_QUEUE_TIMEOUT_SEC = float(os.getenv("EMBEDDING_QUEUE_TIMEOUT_SEC", "3"))
_COOLDOWN_MS = max(0, int(os.getenv("EMBEDDING_COOLDOWN_MS", "80")))
_MAX_BATCH_SIZE = max(1, int(os.getenv("EMBEDDING_MAX_BATCH_SIZE", "8")))
_infer_semaphore = threading.BoundedSemaphore(_MAX_CONCURRENT)


def _get_jwt_secret() -> str:
    secret = os.getenv("SUPPER_SCRET_JWT_KEY", "").strip()
    if not secret:
        raise RuntimeError("SUPPER_SCRET_JWT_KEY is missing")
    return secret


def _validate_jwt_from_header(authorization: str | None) -> None:
    """Accept either ``EMBEDDING_SHARED_BEARER`` (plain string) or a valid HS256 JWT."""
    if not authorization:
        raise PermissionError("Missing Authorization header")

    prefix = "bearer "
    if not authorization.lower().startswith(prefix):
        raise PermissionError("Authorization must be Bearer token")

    token = authorization[len(prefix) :].strip()
    if not token:
        raise PermissionError("Empty Bearer token")

    shared = os.getenv("EMBEDDING_SHARED_BEARER", "").strip()
    if shared and token == shared:
        return

    try:
        secret = _get_jwt_secret()
    except RuntimeError as e:
        raise PermissionError(
            "Server misconfigured: set EMBEDDING_SHARED_BEARER (same value as worker "
            "EMBEDDING_API_KEY) or SUPPER_SCRET_JWT_KEY for JWT mode."
        ) from e

    try:
        jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as e:
        raise PermissionError("JWT expired") from e
    except jwt.InvalidTokenError as e:
        # e.g. PyJWT "Not enough segments" when token is not a JWT (plain API key)
        raise PermissionError(
            "Invalid Bearer token: expected HS256 JWT signed with SUPPER_SCRET_JWT_KEY, "
            "or set EMBEDDING_SHARED_BEARER on this server to the same string as the worker "
            "EMBEDDING_API_KEY (no JWT)."
        ) from e


def _try_acquire_infer_slot() -> bool:
    return _infer_semaphore.acquire(timeout=_QUEUE_TIMEOUT_SEC)


def _release_infer_slot() -> None:
    _infer_semaphore.release()


@app.get("/health", response_model=ApiResponse)
def health() -> JSONResponse:
    try:
        data = {
            "status": "ok",
            "model_loaded": is_model_loaded(),
        }
        return JSONResponse(status_code=200, content={"code": 200, "msg": "ok", "data": data})
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"code": 500, "msg": str(exc), "data": None},
        )


@app.post("/v1/embeddings")
@app.post("/embeddings")
def openai_compatible_embeddings(
    req: OpenAIEmbeddingsRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """
    OpenAI-compatible embeddings API for LangChain ``LocalAIEmbeddings`` / OpenAI client.

    Client calls ``POST {base_url}/embeddings`` with ``base_url`` ending in ``/v1``
    (e.g. ``http://host:6501/v1``). Also exposed as ``/embeddings`` if ``base_url`` has no ``/v1``.
    """
    try:
        _validate_jwt_from_header(authorization)
        texts = [req.input] if isinstance(req.input, str) else list(req.input)
        texts = [t for t in texts if isinstance(t, str) and t.strip()]
        if not texts:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "message": "input must contain at least one non-empty string",
                        "type": "invalid_request_error",
                    }
                },
            )
        if len(texts) > _MAX_BATCH_SIZE:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": (
                            f"Too many input items: {len(texts)} > {_MAX_BATCH_SIZE}. "
                            "Please reduce batch size."
                        ),
                        "type": "rate_limit_error",
                    }
                },
            )

        if not _try_acquire_infer_slot():
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": "Embedding server is busy. Please retry shortly.",
                        "type": "rate_limit_error",
                    }
                },
            )
        try:
            loaded = get_loaded_model()
            vectors = loaded.model.encode(texts, convert_to_numpy=True)
        finally:
            _release_infer_slot()
            if _COOLDOWN_MS > 0:
                time.sleep(_COOLDOWN_MS / 1000.0)
        if vectors.ndim == 1:
            rows = [vectors.tolist()]
        else:
            rows = vectors.tolist()

        model_id = req.model or loaded.model_name
        data = [
            {
                "object": "embedding",
                "embedding": row,
                "index": i,
            }
            for i, row in enumerate(rows)
        ]
        return JSONResponse(
            status_code=200,
            content={
                "object": "list",
                "data": data,
                "model": model_id,
                "usage": {"prompt_tokens": 0, "total_tokens": 0},
            },
        )
    except PermissionError as exc:
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": str(exc),
                    "type": "authentication_error",
                }
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": str(exc),
                    "type": "internal_error",
                }
            },
        )


@app.post("/v1/embed", response_model=ApiResponse)
def embed(req: EmbedRequest, authorization: str | None = Header(default=None)) -> JSONResponse:
    try:
        _validate_jwt_from_header(authorization)
        start = time.perf_counter()
        if not _try_acquire_infer_slot():
            return JSONResponse(
                status_code=429,
                content={"code": 429, "msg": "Embedding server is busy. Please retry shortly.", "data": None},
            )
        try:
            loaded = get_loaded_model()
            vector = loaded.model.encode(req.text, convert_to_numpy=True).tolist()
        finally:
            _release_infer_slot()
            if _COOLDOWN_MS > 0:
                time.sleep(_COOLDOWN_MS / 1000.0)
        processing_time_ms = int((time.perf_counter() - start) * 1000)
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "msg": "success",
                "data": {"vector": vector, "processing_time_ms": processing_time_ms},
            },
        )
    except PermissionError as exc:
        return JSONResponse(
            status_code=401,
            content={"code": 401, "msg": str(exc), "data": None},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"code": 500, "msg": str(exc), "data": None},
        )


if __name__ == "__main__":
    import uvicorn

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=6501,
        timeout_graceful_shutdown=10,
    )
    server = uvicorn.Server(config)
    server.run()
