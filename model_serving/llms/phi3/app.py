from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger("phi3-service")
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PHI3_", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    max_queue_size: int = 200
    max_concurrency: int = 2
    request_timeout_seconds: float = 90.0
    enqueue_timeout_seconds: float = 2.0
    shutdown_wait_seconds: float = 20.0
    ollama_timeout_seconds: float = 75.0
    default_num_predict: int = 512
    model_cache_ttl_seconds: float = 5.0
    default_num_ctx: int = 2048
    default_num_batch: int = 256
    default_num_thread: int = 0
    default_num_gpu: int = -1
    disable_thinking_model_prefixes: str = "qwen3"
    json_repair_attempts: int = 1


settings = Settings()


class ChatMessage(BaseModel):
    role: str = Field(default="user")
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    options: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    request_id: str
    model: str
    created_at: float
    message: dict[str, Any]
    done: bool


@dataclass(slots=True)
class QueueItem:
    request_id: str
    payload: ChatRequest
    future: asyncio.Future[dict[str, Any]]


class RequestQueueManager:
    def __init__(self, cfg: Settings):
        self._cfg = cfg
        self._queue: asyncio.Queue[QueueItem] = asyncio.Queue(maxsize=cfg.max_queue_size)
        self._workers: list[asyncio.Task[None]] = []
        self._running = False
        self._accepting_requests = False
        self._client = ollama.AsyncClient()
        self._known_models: set[str] = set()
        self._model_cache_ts: float = 0.0
        self._disable_thinking_prefixes: tuple[str, ...] = tuple(
            p.strip().lower()
            for p in self._cfg.disable_thinking_model_prefixes.split(",")
            if p.strip()
        )

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def active_workers(self) -> int:
        return len([worker for worker in self._workers if not worker.done()])

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._accepting_requests = True
        for idx in range(self._cfg.max_concurrency):
            worker = asyncio.create_task(self._worker_loop(idx), name=f"ollama-worker-{idx}")
            self._workers.append(worker)
        logger.info(
            "Queue manager started: workers=%s, queue_max=%s",
            self._cfg.max_concurrency,
            self._cfg.max_queue_size,
        )

    async def stop(self) -> None:
        if not self._running:
            return

        logger.info("Queue manager stopping gracefully...")
        self._accepting_requests = False

        # Fail fast all queued-but-not-started requests.
        while not self._queue.empty():
            item = self._queue.get_nowait()
            if not item.future.done():
                item.future.set_exception(
                    HTTPException(
                        status_code=503,
                        detail="Server đang shutdown, request trong queue đã bị hủy.",
                    )
                )
            self._queue.task_done()

        # Wait for in-flight requests to finish.
        try:
            await asyncio.wait_for(self._queue.join(), timeout=self._cfg.shutdown_wait_seconds)
        except asyncio.TimeoutError:
            logger.warning(
                "Graceful shutdown timeout (%ss), forcing worker cancellation.",
                self._cfg.shutdown_wait_seconds,
            )

        self._running = False
        for worker in self._workers:
            worker.cancel()
        for worker in self._workers:
            with contextlib.suppress(asyncio.CancelledError):
                await worker
        self._workers.clear()

    async def submit(self, payload: ChatRequest) -> dict[str, Any]:
        if not self._running or not self._accepting_requests:
            raise HTTPException(status_code=503, detail="Server đang shutdown, tạm ngừng nhận request.")
        await self._ensure_model_available(payload.model)

        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        item = QueueItem(request_id=request_id, payload=payload, future=future)

        try:
            await asyncio.wait_for(
                self._queue.put(item),
                timeout=self._cfg.enqueue_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=503,
                detail="Server đang bận, hàng đợi đầy. Hãy thử lại sau.",
            ) from exc

        try:
            result = await asyncio.wait_for(
                future,
                timeout=self._cfg.request_timeout_seconds,
            )
            return result
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="Request xử lý quá lâu, vui lòng gửi lại.",
            ) from exc
        except HTTPException:
            raise

    async def _worker_loop(self, worker_id: int) -> None:
        logger.info("Worker %s started", worker_id)
        while True:
            item = await self._queue.get()
            try:
                model_name = item.payload.model
                merged_options: dict[str, Any] = {
                    "num_predict": self._cfg.default_num_predict,
                    "temperature": 0,
                    "num_ctx": self._cfg.default_num_ctx,
                    "num_batch": self._cfg.default_num_batch,
                }
                if self._cfg.default_num_thread > 0:
                    merged_options["num_thread"] = self._cfg.default_num_thread
                if self._cfg.default_num_gpu >= 0:
                    merged_options["num_gpu"] = self._cfg.default_num_gpu
                if item.payload.options:
                    merged_options.update(item.payload.options)
                think_mode = self._resolve_think_mode(model_name, item.payload.options)
                response_format = self._resolve_response_format(model_name, item.payload.messages)
                merged_options.pop("think", None)

                response = await asyncio.wait_for(
                    self._client.chat(
                        model=model_name,
                        messages=[msg.model_dump() for msg in item.payload.messages],
                        stream=False,
                        think=think_mode,
                        format=response_format,
                        options=merged_options,
                    ),
                    timeout=self._cfg.ollama_timeout_seconds,
                )
                message_payload = response["message"]
                if hasattr(message_payload, "model_dump"):
                    message_payload = message_payload.model_dump()
                elif not isinstance(message_payload, dict):
                    message_payload = {
                        "role": getattr(message_payload, "role", "assistant"),
                        "content": str(getattr(message_payload, "content", "")),
                    }
                message_payload.pop("thinking", None)
                if response_format == "json":
                    raw_content = str(message_payload.get("content", ""))
                    try:
                        message_payload["content"] = self._normalize_json_text(raw_content)
                    except HTTPException as first_exc:
                        repaired = await self._attempt_json_repair(
                            model_name=model_name,
                            original_messages=[msg.model_dump() for msg in item.payload.messages],
                            broken_content=raw_content,
                            merged_options=merged_options,
                            think_mode=think_mode,
                            response_format=response_format,
                        )
                        if repaired is None:
                            raise first_exc
                        message_payload["content"] = repaired

                payload = {
                    "request_id": item.request_id,
                    "model": model_name,
                    "created_at": time.time(),
                    "message": message_payload,
                    "done": response.get("done", True),
                }
                if not item.future.done():
                    item.future.set_result(payload)
            except asyncio.TimeoutError:
                logger.warning(
                    "Worker %s timeout for request %s after %ss",
                    worker_id,
                    item.request_id,
                    self._cfg.ollama_timeout_seconds,
                )
                if not item.future.done():
                    item.future.set_exception(
                        HTTPException(
                            status_code=504,
                            detail="Ollama xử lý quá thời gian cho phép, vui lòng thử lại.",
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Worker %s failed request %s", worker_id, item.request_id)
                if not item.future.done():
                    item.future.set_exception(
                        HTTPException(status_code=502, detail=f"Ollama error: {exc}")
                    )
            finally:
                self._queue.task_done()

    async def _ensure_model_available(self, model_name: str) -> None:
        await self._refresh_model_cache_if_needed()
        if model_name not in self._known_models:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Model '{model_name}' không tồn tại trong Ollama local. "
                    f"Các model hiện có: {sorted(self._known_models)}"
                ),
            )

    async def _refresh_model_cache_if_needed(self) -> None:
        now = time.time()
        if self._known_models and (now - self._model_cache_ts) < self._cfg.model_cache_ttl_seconds:
            return

        try:
            raw_models = await self._client.list()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"Không thể lấy danh sách model từ Ollama: {exc}",
            ) from exc

        models: set[str] = set()
        for item in raw_models.get("models", []):
            if isinstance(item, dict):
                name = item.get("model") or item.get("name")
            else:
                name = getattr(item, "model", None) or getattr(item, "name", None)
            if name:
                models.add(str(name))

        self._known_models = models
        self._model_cache_ts = now

    def _resolve_think_mode(self, model_name: str, req_options: dict[str, Any] | None) -> bool | None:
        model_key = model_name.lower()
        if any(model_key.startswith(prefix) for prefix in self._disable_thinking_prefixes):
            return False

        if req_options and "think" in req_options:
            return bool(req_options["think"])
        return None

    def _resolve_response_format(
        self, model_name: str, messages: list[ChatMessage]
    ) -> str | dict[str, Any] | None:
        model_key = model_name.lower()
        if model_key.startswith("qwen3"):
            return {
                "type": "object",
                "properties": {
                    "tham_chieu": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "van_ban_tham_chieu": {"type": ["string", "null"]},
                                "loai_tham_chieu": {"type": "string", "enum": ["chinh_no", "khac"]},
                                "diem": {"type": ["integer", "null"]},
                                "khoan": {"type": ["integer", "null"]},
                                "dieu": {"type": ["integer", "null"]},
                            },
                            "required": [
                                "van_ban_tham_chieu",
                                "loai_tham_chieu",
                                "diem",
                                "khoan",
                                "dieu",
                            ],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["tham_chieu"],
                "additionalProperties": False,
            }

        for msg in messages:
            if msg.role == "system" and "json" in msg.content.lower():
                return "json"
        return None

    async def _attempt_json_repair(
        self,
        model_name: str,
        original_messages: list[dict[str, Any]],
        broken_content: str,
        merged_options: dict[str, Any],
        think_mode: bool | None,
        response_format: str | None,
    ) -> str | None:
        if self._cfg.json_repair_attempts <= 0:
            return None

        repair_messages = [
            *original_messages,
            {"role": "assistant", "content": broken_content},
            {
                "role": "user",
                "content": (
                    "JSON ở trên bị lỗi cú pháp. "
                    "Hãy trả lại DUY NHẤT một JSON object hợp lệ, không markdown, không giải thích."
                ),
            },
        ]

        for _ in range(self._cfg.json_repair_attempts):
            repair_resp = await asyncio.wait_for(
                self._client.chat(
                    model=model_name,
                    messages=repair_messages,
                    stream=False,
                    think=think_mode,
                    format=response_format,
                    options=merged_options,
                ),
                timeout=self._cfg.ollama_timeout_seconds,
            )
            repair_msg = repair_resp["message"]
            if hasattr(repair_msg, "model_dump"):
                repair_msg = repair_msg.model_dump()
            content = str(repair_msg.get("content", "")) if isinstance(repair_msg, dict) else str(repair_msg)
            try:
                return self._normalize_json_text(content)
            except HTTPException:
                repair_messages.append({"role": "assistant", "content": content})
                repair_messages.append(
                    {
                        "role": "user",
                        "content": "Vẫn sai JSON. Chỉ xuất đúng 1 JSON object hợp lệ.",
                    }
                )
        return None

    @staticmethod
    def _normalize_json_text(text: str) -> str:
        stripped = text.strip()
        try:
            parsed = json.loads(stripped)
            return json.dumps(parsed, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            pass

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            candidate = stripped[start : end + 1]
            try:
                parsed = json.loads(candidate)
                return json.dumps(parsed, ensure_ascii=False)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=502,
                    detail=f"Model không trả JSON hợp lệ: {exc}",
                ) from exc

        raise HTTPException(
            status_code=502,
            detail="Model không trả JSON hợp lệ (không tìm thấy JSON object).",
        )


queue_manager = RequestQueueManager(settings)
app = FastAPI(title="Phi3 Self-hosted Queue API", version="1.0.0")


@app.on_event("startup")
async def on_startup() -> None:
    await queue_manager.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Received shutdown signal, draining queue before exit...")
    await queue_manager.stop()


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model": "required_in_request",
        "queue_size": queue_manager.queue_size,
        "active_workers": queue_manager.active_workers,
        "max_queue_size": settings.max_queue_size,
    }


@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(req: ChatRequest) -> ChatResponse:
    if req.stream:
        raise HTTPException(status_code=400, detail="stream=true chưa được hỗ trợ ở service này")
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages không được để trống")

    result = await queue_manager.submit(req)
    return ChatResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        workers=1,
    )
