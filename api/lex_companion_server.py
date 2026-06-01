import asyncio
import importlib
import importlib.util
import os
import signal
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Awaitable, Callable

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from api.db.models import run_migration
from api.db.models import POSTGRES_CONFIG as postgres_config
from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio
from api.utils.minio_conn import MINIO_CONFIG
from api.utils.redis_conn import REDIS_CONN
from api.worker.task_execution import start_task_worker, stop_task_worker
from api.utils.llm_client import LLMProvider
from api.utils.llm_client import config
logger = setup_logging()

llm_client = LLMProvider(config)
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Handle app startup and shutdown lifecycle."""
    run_migration()
    logger.info(f"Connected to Postgres database successfully with config :{postgres_config}")
    #### connect to minio
    minio_conn = LexCompanionMinio()
    if not minio_conn.health():
        logger.error("Minio connection failed")
        raise Exception("Minio connection failed")
    logger.info(f"Minio connection successful with config :{MINIO_CONFIG}")

    if REDIS_CONN.is_alive() and REDIS_CONN.health():
        logger.info("Redis connection OK; starting background task worker")
        app.state.task_worker_task, app.state.task_worker_stop = start_task_worker()
    else:
        logger.warning("Redis unavailable; background task worker not started")
        app.state.task_worker_task = None
        app.state.task_worker_stop = None

    if getattr(app.state, "task_worker_task", None) is not None:
        try:
            from api.worker.document_parse import warmup_docling

            logger.info("Preloading Docling (OCR) in background thread...")
            await asyncio.to_thread(warmup_docling)
            logger.info("Docling preload finished")
        except Exception as e:
            logger.warning(f"Docling warmup failed (first parse will still work): {e}")

    app.state.reranker = None
    if os.getenv("RERANK_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            from deepagent.core.rerank.rerank import init_reranker

            logger.info("Loading bge-reranker-v2-m3 (FlagEmbedding)...")
            app.state.reranker = await asyncio.to_thread(init_reranker)
            logger.info("bge-reranker-v2-m3 ready")
        except Exception as e:
            logger.warning(f"Reranker init failed (search will work without rerank): {e}")
    else:
        logger.info("Reranker disabled (RERANK_ENABLED=false)")

    logger.info("FastAPI server started successfully on port 5999")
    yield
    if getattr(app.state, "task_worker_task", None) is not None:
        await stop_task_worker(app.state.task_worker_task, app.state.task_worker_stop)
        logger.info("Background task worker stopped")
    logger.info("FastAPI lifespan shutdown completed")


def create_app() -> FastAPI:
    """Create FastAPI app and attach routers/middleware."""
    app = FastAPI(title="Lex Companion API", version="0.1.1", lifespan=app_lifespan)
    app.state.active_requests = 0
    app.state.is_shutting_down = False
    app.state.shutdown_event = asyncio.Event()

    @app.middleware("http")
    async def graceful_shutdown_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Reject new requests while shutdown is in progress.
        if request.app.state.is_shutting_down:
            return JSONResponse(
                status_code=503,
                content={"detail": "Server is shutting down. Please retry later."},
            )

        request.app.state.active_requests += 1
        try:
            return await call_next(request)
        finally:
            request.app.state.active_requests -= 1
            if (
                request.app.state.is_shutting_down
                and request.app.state.active_requests == 0
            ):
                request.app.state.shutdown_event.set()

    # CORS: mọi origin, mọi method, mọi header request/response (expose).
    # Lưu ý: allow_origins=["*"] không tương thích với allow_credentials=True.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    load_routers(app)

    return app


def load_routers(app: FastAPI) -> None:
    """Import and include all routers from api/apps/routers."""
    routers_dir = Path(__file__).resolve().parent / "apps" / "routers"
    loaded_count = 0

    for router_file in routers_dir.glob("*.py"):
        if router_file.name.startswith("_"):
            continue

        module_name = f"api.apps.routers.{router_file.stem}"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            module_spec = importlib.util.spec_from_file_location(module_name, router_file)
            if module_spec is None or module_spec.loader is None:
                logger.warning(f"Cannot load router module: {router_file}")
                continue
            module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(module)
        router = getattr(module, "router", None)

        if router is None:
            logger.warning(f"Router not found in module: {module_name}")
            continue

        app.include_router(router)
        loaded_count += 1
        logger.info(f"Router loaded: {module_name}")

    if loaded_count == 0:
        logger.warning("No routers were loaded from api/apps/routers")


async def run_server() -> None:
    """Run uvicorn server with graceful shutdown signal handling."""
    app = create_app()
    config = uvicorn.Config(app=app, host="0.0.0.0", port=5999, log_config=None ,reload=True)
    server = uvicorn.Server(config)

    loop = asyncio.get_running_loop()
    signal_received = asyncio.Event()

    def handle_shutdown_signal(sig: signal.Signals) -> None:
        if app.state.is_shutting_down:
            return

        app.state.is_shutting_down = True
        logger.info(f"Received signal {sig.name}. Starting graceful shutdown...")
        signal_received.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, handle_shutdown_signal, sig)

    server_task = asyncio.create_task(server.serve())
    signal_task = asyncio.create_task(signal_received.wait())
    done, pending = await asyncio.wait(
        [server_task, signal_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()

    if server_task in done:
        # Server exited early (for example, bind failure on occupied port).
        with suppress(SystemExit):
            await server_task
        return

    # Tell uvicorn to stop accepting new connections.
    server.should_exit = True

    if app.state.active_requests > 0:
        logger.info(
            f"Waiting for {app.state.active_requests} active request(s) to finish..."
        )
        await app.state.shutdown_event.wait()

    logger.info("All requests finished. Server shutdown complete.")
    with suppress(SystemExit):
        await server_task


if __name__ == "__main__":
    asyncio.run(run_server())
