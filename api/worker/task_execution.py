"""Redis Streams consumer: pulls tasks and runs document parsing / embedding pipelines."""

from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import suppress

from api.utils.logger import setup_logging
from api.utils.redis_conn import REDIS_CONN
from api.worker.document_parse import normalize_task_type, run_parse_document_job

logger = setup_logging()

STREAM_KEY = os.getenv("LEX_TASK_STREAM", "lex:tasks")
GROUP_NAME = os.getenv("LEX_TASK_GROUP", "lex-workers")
CONSUMER_NAME = os.getenv(
    "LEX_TASK_CONSUMER",
    f"lex-worker-{os.getpid()}-{uuid.uuid4().hex[:6]}",
)


async def _dispatch_task(payload: dict) -> None:
    task_type = normalize_task_type(payload.get("type"))
    if task_type == "parse_document":
        doc_id = payload.get("document_id")
        if not doc_id:
            raise ValueError("parse_document requires document_id")
        parse_type = str(payload.get("parse_type") or "docdealing")
        await asyncio.to_thread(run_parse_document_job, str(doc_id), parse_type)
        return
    logger.warning("Unhandled task type=%s keys=%s", task_type, list(payload.keys()))


async def _worker_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        if not REDIS_CONN.is_alive() or REDIS_CONN.REDIS is None:
            logger.warning("Redis unavailable; task worker idle, retry in 5s")
            try:
                await asyncio.wait_for(stop.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
            continue
        try:
            msg = await asyncio.to_thread(
                REDIS_CONN.queue_consumer,
                STREAM_KEY,
                GROUP_NAME,
                CONSUMER_NAME,
            )
        except Exception:
            logger.exception("queue_consumer failed")
            await asyncio.sleep(1)
            continue
        if msg is None:
            continue
        try:
            payload = msg.get_message()
            await _dispatch_task(payload)
            msg.ack()
        except Exception:
            logger.exception(
                "Task failed msg_id=%s; leaving unacked for retry",
                msg.get_msg_id(),
            )


def start_task_worker() -> tuple[asyncio.Task, asyncio.Event]:
    stop = asyncio.Event()
    task = asyncio.create_task(_worker_loop(stop), name="lex-redis-task-worker")
    return task, stop


async def stop_task_worker(task: asyncio.Task, stop: asyncio.Event) -> None:
    stop.set()
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
