"""Redis Streams consumer: pulls tasks and runs document parsing / embedding pipelines."""

from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import suppress
from datetime import datetime
from typing import Any

from elasticsearch.helpers import bulk

from api.apps.services.hf_dataset_service import build_article_id, import_phapdien_to_postgres
from api.apps.services.legal_service import LegalIngestionJobService
from api.db.models import DB, LegalArticle, LegalSubject, LegalTopic, LegalTreeNode
from api.utils.elastic_chunk_index import (
    embed_documents_with_backpressure,
    embedding_from_env,
    get_elasticsearch_client,
)
from api.utils.logger import setup_logging
from api.utils.redis_conn import REDIS_CONN
from api.worker.document_parse import normalize_task_type, run_parse_document_job
from deepagent.core.text_splitters.legal_article_split import (
    LegalArticleContentChunk,
    LegalArticleContentSplitter,
)

logger = setup_logging()

STREAM_KEY = os.getenv("LEX_TASK_STREAM", "lex:tasks")
GROUP_NAME = os.getenv("LEX_TASK_GROUP", "lex-workers")
CONSUMER_NAME = os.getenv(
    "LEX_TASK_CONSUMER",
    f"lex-worker-{os.getpid()}-{uuid.uuid4().hex[:6]}",
)

LEX_CHUNKS_INDEX = os.getenv("LEX_CHUNKS_INDEX", "lex_chunks_v1")
LEGAL_ES_BULK_SIZE = max(100, int(os.getenv("LEGAL_ES_BULK_SIZE", "500")))
LEGAL_VECTOR_DIMS = int(os.getenv("LEGAL_VECTOR_DIMS", "1024"))
LEGAL_ARTICLE_EMBED_BATCH = max(8, int(os.getenv("LEGAL_ARTICLE_EMBED_BATCH", "500")))

_VECTOR_MAPPING = {
    "type": "dense_vector",
    "dims": LEGAL_VECTOR_DIMS,
    "index": True,
    "similarity": "cosine",
}

LEX_CHUNKS_MAPPING: dict[str, Any] = {
    "properties": {
        "article_id": {"type": "keyword"},
        "topic_id": {"type": "keyword"},
        "topic_title": {"type": "keyword"},
        "topic_note": {"type": "keyword"},
        "subject_id": {"type": "keyword"},
        "subject_title": {"type": "keyword"},
        "source_subject": {"type": "keyword"},
        "article_title": {"type": "keyword"},
        "chapter_title": {"type": "keyword"},
        "source_note_text": {"type": "keyword"},
        "source_link": {"type": "keyword"},
        "related_note_text": {"type": "keyword"},
        "content_text": {"type": "text"},
        "content_vector": _VECTOR_MAPPING,
        "max_chunks": {"type": "integer"},
        "order": {"type": "integer"},
        "parent_chunk_id": {"type": "keyword"},
        "created_at": {"type": "date"},
    }
}


def _format_es_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def ensure_lex_chunks_index(es) -> None:
    """Tạo index lex_chunks nếu chưa tồn tại."""
    if es.indices.exists(index=LEX_CHUNKS_INDEX):
        return
    es.indices.create(index=LEX_CHUNKS_INDEX, mappings=LEX_CHUNKS_MAPPING)
    logger.info(f"Created Elasticsearch index={LEX_CHUNKS_INDEX}")


def _reset_lex_chunks_index(es) -> None:
    """Xóa và tạo lại lex_chunks để đảm bảo mapping vector đúng."""
    if es.indices.exists(index=LEX_CHUNKS_INDEX):
        es.indices.delete(index=LEX_CHUNKS_INDEX)
    es.indices.create(index=LEX_CHUNKS_INDEX, mappings=LEX_CHUNKS_MAPPING)
    logger.info(f"Reset Elasticsearch index={LEX_CHUNKS_INDEX}")


def _bulk_actions(es, actions: list[dict[str, Any]]) -> int:
    if not actions:
        return 0
    success, errors = bulk(es, actions, chunk_size=LEGAL_ES_BULK_SIZE, refresh="wait_for")
    if errors:
        raise RuntimeError(f"Elasticsearch bulk failed: {errors[:3]}")
    return success


def _embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    embeddings = embedding_from_env()
    vectors = embed_documents_with_backpressure(embeddings, texts)
    # Guard: zip(pending, vectors) must be 1:1 or ES gets wrong chunk↔vector pairs.
    if len(vectors) != len(texts):
        raise RuntimeError(
            f"Embedding count mismatch: {len(vectors)} != {len(texts)} "
            "(embedding API returned fewer vectors than inputs)"
        )
    for idx, vec in enumerate(vectors):
        if len(vec) != LEGAL_VECTOR_DIMS:
            raise RuntimeError(
                f"Unexpected vector dims at index={idx}: {len(vec)} != {LEGAL_VECTOR_DIMS}"
            )
    return vectors


def _load_title_lookups() -> tuple[dict[str, str], dict[str, str], dict[str, str | None]]:
    subject_titles = {
        row.subject_id: row.subject_title
        for row in LegalSubject.select(LegalSubject.subject_id, LegalSubject.subject_title)
        if row.subject_id
    }
    topic_titles: dict[str, str] = {
        row.topic_id: row.topic_title_vi
        for row in LegalTopic.select(LegalTopic.topic_id, LegalTopic.topic_title_vi)
        if row.topic_id and row.topic_title_vi
    }
    topic_notes: dict[str, str | None] = {
        row.topic_id: row.topic_note
        for row in LegalTopic.select(LegalTopic.topic_id, LegalTopic.topic_note)
        if row.topic_id
    }
    for row in LegalTreeNode.select(
        LegalTreeNode.node_id,
        LegalTreeNode.title,
        LegalTreeNode.kind,
    ):
        if row.kind == "topic" and row.node_id and row.title:
            topic_titles.setdefault(row.node_id, row.title)
    return subject_titles, topic_titles, topic_notes


def _extract_source_link(row: LegalArticle) -> str | None:
    links = row.source_links if isinstance(row.source_links, list) else []
    if links:
        first = links[0]
        if isinstance(first, dict):
            return first.get("href") or first.get("url") or first.get("link")
        text = str(first).strip()
        return text or None
    return row.source_url


def _format_source_subject(row: LegalArticle, subject_titles: dict[str, str]) -> str | None:
    title = row.subject_title or subject_titles.get(row.subject_id or "")
    if row.subject_number is not None and title:
        return f"{row.subject_number}. {title}"
    return title


def _lex_chunk_doc_id(article_id: str, chunk: LegalArticleContentChunk) -> str:
    if chunk.order is None:
        return article_id
    return f"{article_id}_{chunk.order}"


def _build_lex_chunk_source(
    row: LegalArticle,
    chunk: LegalArticleContentChunk,
    *,
    article_id: str,
    subject_titles: dict[str, str],
    topic_titles: dict[str, str],
    topic_notes: dict[str, str | None],
) -> dict[str, Any]:
    topic_id = row.topic_id or ""
    return {
        "article_id": article_id,
        "topic_id": topic_id or None,
        "topic_title": row.topic_title or topic_titles.get(topic_id),
        "topic_note": topic_notes.get(topic_id),
        "subject_id": row.subject_id,
        "subject_title": row.subject_title or subject_titles.get(row.subject_id or ""),
        "source_subject": _format_source_subject(row, subject_titles),
        "article_title": row.article_title,
        "chapter_title": row.chapter_title,
        "source_note_text": row.source_note_text,
        "source_link": _extract_source_link(row),
        "related_note_text": row.related_note_text,
        "content_text": chunk.text,
        "max_chunks": chunk.max_chunks,
        "order": chunk.order,
        "parent_chunk_id": chunk.parent_chunk_id,
        "created_at": _format_es_date(row.created_at),
    }


def _flush_lex_chunk_batch(
    es,
    pending: list[tuple[str, dict[str, Any], str]],
) -> int:
    """Embed ``content_text`` của từng chunk rồi bulk index."""
    texts = [embed_text for _, _, embed_text in pending]
    vectors = _embed_texts(texts)
    actions = [
        {
            "_op_type": "index",
            "_index": LEX_CHUNKS_INDEX,
            "_id": chunk_id,
            "_source": {**source, "content_vector": vector},
        }
        for (chunk_id, source, _), vector in zip(pending, vectors)
    ]
    return _bulk_actions(es, actions)


def _index_lex_chunks_from_articles(
    es,
    *,
    splitter: LegalArticleContentSplitter,
    subject_titles: dict[str, str],
    topic_titles: dict[str, str],
    topic_notes: dict[str, str | None],
) -> int:
    indexed = 0
    pending: list[tuple[str, dict[str, Any], str]] = []

    for row in LegalArticle.select():
        article_id = build_article_id(row.subject_id or "", row.article_anchor, row.article_title)
        chunks = splitter.split_with_metadata(
            row.content_text or "",
            article_id=article_id,
            content_char_len=row.content_char_len,
        )
        for chunk in chunks:
            chunk_id = _lex_chunk_doc_id(article_id, chunk)
            source = _build_lex_chunk_source(
                row,
                chunk,
                article_id=article_id,
                subject_titles=subject_titles,
                topic_titles=topic_titles,
                topic_notes=topic_notes,
            )
            pending.append((chunk_id, source, chunk.text))

            if len(pending) >= LEGAL_ARTICLE_EMBED_BATCH:
                indexed += _flush_lex_chunk_batch(es, pending)
                pending = []
                logger.info(f"Indexed lex_chunks batch total={indexed}")

    if pending:
        indexed += _flush_lex_chunk_batch(es, pending)
    return indexed


@DB.connection_context()
def sync_phapdien_postgres_to_elasticsearch(job_id: int) -> dict[str, int]:
    """
    Đọc legal_articles từ PostgreSQL, split content_text dài, embed từng chunk,
    bulk index vào lex_chunks.
    """
    es = get_elasticsearch_client()
    _reset_lex_chunks_index(es)

    subject_titles, topic_titles, topic_notes = _load_title_lookups()
    splitter = LegalArticleContentSplitter()

    logger.info(f"sync_phapdien_to_es job_id={job_id} indexing lex_chunks from legal_articles")
    chunks_indexed = _index_lex_chunks_from_articles(
        es,
        splitter=splitter,
        subject_titles=subject_titles,
        topic_titles=topic_titles,
        topic_notes=topic_notes,
    )

    stats = {LEX_CHUNKS_INDEX: chunks_indexed}
    logger.info(f"sync_phapdien_postgres_to_elasticsearch job_id={job_id} stats={stats}")
    return stats


def run_phapdien_import_pipeline(job_id: int, dataset_name: str) -> None:
    """HF → PostgreSQL → Elasticsearch; cập nhật LegalIngestionJob khi xong."""
    try:
        pg_result = import_phapdien_to_postgres(
            dataset_name=dataset_name,
            job_id=job_id,
            finalize=False,
        )
        es_stats = sync_phapdien_postgres_to_elasticsearch(job_id)
        LegalIngestionJobService.mark_finished(
            job_id,
            status="completed",
            total_rows=pg_result.get("total_rows"),
            success_rows=pg_result.get("success_rows"),
            failed_rows=pg_result.get("failed_rows"),
        )
        logger.info(
            f"run_phapdien_import_pipeline done job_id={job_id} "
            f"postgres={pg_result.get('success_rows')} es={es_stats}"
        )
    except Exception as exc:
        logger.error(f"run_phapdien_import_pipeline failed job_id={job_id}: {exc}")
        LegalIngestionJobService.mark_finished(
            job_id,
            status="failed",
            error_message=str(exc),
        )
        raise


async def _dispatch_task(payload: dict) -> None:
    task_type = normalize_task_type(payload.get("type"))
    if task_type == "parse_document":
        doc_id = payload.get("document_id")
        if not doc_id:
            raise ValueError("parse_document requires document_id")
        parse_type = str(payload.get("parse_type") or "docdealing")
        await asyncio.to_thread(run_parse_document_job, str(doc_id), parse_type)
        return
    if task_type == "import_hf_phapdien":
        job_id = payload.get("job_id")
        dataset_name = payload.get("dataset_name")
        if job_id is None or not dataset_name:
            raise ValueError("import_hf_phapdien requires job_id and dataset_name")
        await asyncio.to_thread(
            run_phapdien_import_pipeline,
            int(job_id),
            str(dataset_name),
        )
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


## chay ham sync_phapdien_postgres_to_elasticsearch
if __name__ == "__main__":
    sync_phapdien_postgres_to_elasticsearch(1)