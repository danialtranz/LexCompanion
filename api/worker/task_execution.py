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
from api.db.models import (
    DB,
    LegalArticle,
    LegalGlossary,
    LegalSubject,
    LegalTopic,
    LegalTreeNode,
)
from api.utils.elastic_chunk_index import (
    embed_documents_with_backpressure,
    embedding_from_env,
    get_elasticsearch_client,
)
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

LEGAL_ARTICLES_INDEX = os.getenv("LEGAL_ARTICLES_INDEX", "legal_articles_v1")
LEGAL_GLOSSARY_INDEX = os.getenv("LEGAL_GLOSSARY_INDEX", "legal_glossary_v1")
LEGAL_SUBJECTS_INDEX = os.getenv("LEGAL_SUBJECTS_INDEX", "legal_subjects_v1")
LEGAL_ES_BULK_SIZE = max(100, int(os.getenv("LEGAL_ES_BULK_SIZE", "500")))
LEGAL_VECTOR_DIMS = int(os.getenv("LEGAL_VECTOR_DIMS", "1024"))
LEGAL_ARTICLE_EMBED_BATCH = max(8, int(os.getenv("LEGAL_ARTICLE_EMBED_BATCH", "500")))

_SOURCE_LINKS_MAPPING = {
    "type": "nested",
    "properties": {
        "text": {"type": "text"},
        "href": {"type": "keyword"},
    },
}

_VECTOR_MAPPING = {
    "type": "dense_vector",
    "dims": LEGAL_VECTOR_DIMS,
    "index": True,
    "similarity": "cosine",
}

LEGAL_INDEX_DEFINITIONS: dict[str, dict[str, Any]] = {
    LEGAL_ARTICLES_INDEX: {
        "properties": {
            "article_id": {"type": "keyword"},
            "subject_id": {"type": "keyword"},
            "topic_id": {"type": "keyword"},
            "subject_title": {"type": "text"},
            "topic_title": {"type": "text"},
            "chapter_title": {"type": "text"},
            "article_title": {"type": "text"},
            "content_text": {"type": "text"},
            "source_note_text": {"type": "text"},
            "related_note_text": {"type": "text"},
            "source_url": {"type": "keyword"},
            "source_links": _SOURCE_LINKS_MAPPING,
            "scraped_at": {"type": "date"},
            "content_vector": _VECTOR_MAPPING,
        }
    },
    LEGAL_GLOSSARY_INDEX: {
        "properties": {
            "term": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "definition": {"type": "text"},
            "subject_id": {"type": "keyword"},
            "topic_id": {"type": "keyword"},
            "term_vector": _VECTOR_MAPPING,
        }
    },
    LEGAL_SUBJECTS_INDEX: {
        "properties": {
            "subject_id": {"type": "keyword"},
            "topic_id": {"type": "keyword"},
            "subject_title": {"type": "text"},
            "topic_title": {"type": "text"},
            "subject_vector": _VECTOR_MAPPING,
        }
    },
}


def _format_es_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def ensure_legal_elasticsearch_indices(es) -> None:
    """Tạo 3 index legal_* (mapping gồm dense_vector 1024 chiều)."""
    for index_name, body in LEGAL_INDEX_DEFINITIONS.items():
        if es.indices.exists(index=index_name):
            continue
        es.indices.create(index=index_name, mappings=body)
        logger.info(f"Created Elasticsearch index={index_name}")


def _reset_legal_elasticsearch_indices(es) -> None:
    """Xóa và tạo lại index để đảm bảo mapping vector đúng."""
    for index_name, body in LEGAL_INDEX_DEFINITIONS.items():
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)
        es.indices.create(index=index_name, mappings=body)
        logger.info(f"Reset Elasticsearch index={index_name}")


def _bulk_actions(es, actions: list[dict[str, Any]]) -> int:
    if not actions:
        return 0
    success, errors = bulk(es, actions, chunk_size=LEGAL_ES_BULK_SIZE, refresh="wait_for")
    if errors:
        raise RuntimeError(f"Elasticsearch bulk failed: {errors[:3]}")
    return success


def _join_embed_parts(*parts: Any) -> str:
    chunks = [str(p).strip() for p in parts if p is not None and str(p).strip()]
    text = "\n".join(chunks).strip()
    return text or "."


def _build_article_embed_text(
    *,
    chapter_title: str | None,
    article_title: str | None,
    content_text: str | None,
    topic_title: str | None,
    subject_title: str | None,
) -> str:
    return _join_embed_parts(
        f"Chủ đề: {topic_title}" if topic_title else None,
        f"Đề mục: {subject_title}" if subject_title else None,
        chapter_title,
        article_title,
        content_text,
    )


def _build_glossary_embed_text(*, term: str | None, definition: str | None) -> str:
    return _join_embed_parts(term, definition)


def _build_subject_embed_text(*, topic_title: str | None, subject_title: str | None) -> str:
    return _join_embed_parts(topic_title, subject_title)


def _embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    embeddings = embedding_from_env()
    vectors = embed_documents_with_backpressure(embeddings, texts)
    if len(vectors) != len(texts):
        raise RuntimeError(f"Embedding count mismatch: {len(vectors)} != {len(texts)}")
    for idx, vec in enumerate(vectors):
        if len(vec) != LEGAL_VECTOR_DIMS:
            raise RuntimeError(
                f"Unexpected vector dims at index={idx}: {len(vec)} != {LEGAL_VECTOR_DIMS}"
            )
    return vectors


def _load_title_lookups() -> tuple[dict[str, str], dict[str, str]]:
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
    for row in LegalTreeNode.select(
        LegalTreeNode.node_id,
        LegalTreeNode.title,
        LegalTreeNode.kind,
    ):
        if row.kind == "topic" and row.node_id and row.title:
            topic_titles.setdefault(row.node_id, row.title)
    return subject_titles, topic_titles


def _build_subject_actions(
    rows: list[LegalSubject],
    topic_titles: dict[str, str],
    vectors: list[list[float]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for row, vector in zip(rows, vectors):
        topic_id = row.topic_id or ""
        actions.append(
            {
                "_op_type": "index",
                "_index": LEGAL_SUBJECTS_INDEX,
                "_id": row.subject_id,
                "_source": {
                    "subject_id": row.subject_id,
                    "topic_id": topic_id or None,
                    "subject_title": row.subject_title,
                    "topic_title": topic_titles.get(topic_id or ""),
                    "subject_vector": vector,
                },
            }
        )
    return actions


def _build_glossary_actions(
    rows: list[LegalGlossary],
    vectors: list[list[float]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for row, vector in zip(rows, vectors):
        definition = _join_embed_parts(row.en, row.note, row.category)
        actions.append(
            {
                "_op_type": "index",
                "_index": LEGAL_GLOSSARY_INDEX,
                "_id": str(row.id),
                "_source": {
                    "term": row.vi,
                    "definition": definition or None,
                    "category": row.category,
                    "term_vector": vector,
                },
            }
        )
    return actions


def _article_source(
    row: LegalArticle,
    *,
    subject_titles: dict[str, str],
    topic_titles: dict[str, str],
    content_vector: list[float],
) -> dict[str, Any]:
    topic_id = row.topic_id or ""
    article_id = build_article_id(row.subject_id or "", row.article_anchor, row.article_title)
    source_links = row.source_links if isinstance(row.source_links, list) else []
    return {
        "article_id": article_id,
        "subject_id": row.subject_id,
        "topic_id": topic_id or None,
        "subject_title": row.subject_title or subject_titles.get(row.subject_id or ""),
        "topic_title": row.topic_title or topic_titles.get(topic_id or ""),
        "chapter_title": row.chapter_title,
        "article_title": row.article_title,
        "content_text": row.content_text,
        "source_note_text": row.source_note_text,
        "related_note_text": row.related_note_text,
        "source_url": row.source_url,
        "source_links": source_links,
        "scraped_at": _format_es_date(row.scraped_at),
        "content_vector": content_vector,
    }


def _index_articles_with_vectors(
    es,
    *,
    subject_titles: dict[str, str],
    topic_titles: dict[str, str],
) -> int:
    indexed = 0
    batch_rows: list[LegalArticle] = []
    for row in LegalArticle.select():
        batch_rows.append(row)
        if len(batch_rows) < LEGAL_ARTICLE_EMBED_BATCH:
            continue
        indexed += _index_article_batch(
            es,
            batch_rows,
            subject_titles=subject_titles,
            topic_titles=topic_titles,
        )
        batch_rows = []
        logger.info(f"Indexed legal articles batch total={indexed}")
    if batch_rows:
        indexed += _index_article_batch(
            es,
            batch_rows,
            subject_titles=subject_titles,
            topic_titles=topic_titles,
        )
    return indexed


def _index_article_batch(
    es,
    rows: list[LegalArticle],
    *,
    subject_titles: dict[str, str],
    topic_titles: dict[str, str],
) -> int:
    texts = [
        _build_article_embed_text(
            chapter_title=row.chapter_title,
            article_title=row.article_title,
            content_text=row.content_text,
            topic_title=row.topic_title or topic_titles.get((row.topic_id or "")),
            subject_title=row.subject_title or subject_titles.get(row.subject_id or ""),
        )
        for row in rows
    ]
    vectors = _embed_texts(texts)
    actions = []
    for row, vector in zip(rows, vectors):
        article_id = build_article_id(row.subject_id or "", row.article_anchor, row.article_title)
        actions.append(
            {
                "_op_type": "index",
                "_index": LEGAL_ARTICLES_INDEX,
                "_id": article_id,
                "_source": _article_source(
                    row,
                    subject_titles=subject_titles,
                    topic_titles=topic_titles,
                    content_vector=vector,
                ),
            }
        )
    return _bulk_actions(es, actions)


def _index_subjects_with_vectors(
    es,
    *,
    topic_titles: dict[str, str],
) -> int:
    rows = list(LegalSubject.select())
    texts = [
        _build_subject_embed_text(
            topic_title=topic_titles.get((row.topic_id or "")),
            subject_title=row.subject_title,
        )
        for row in rows
    ]
    vectors = _embed_texts(texts)
    return _bulk_actions(es, _build_subject_actions(rows, topic_titles, vectors))


def _index_glossary_with_vectors(es) -> int:
    rows = list(LegalGlossary.select())
    texts = [
        _build_glossary_embed_text(
            term=row.vi,
            definition=_join_embed_parts(row.en, row.note, row.category),
        )
        for row in rows
    ]
    vectors = _embed_texts(texts)
    return _bulk_actions(es, _build_glossary_actions(rows, vectors))


@DB.connection_context()
def sync_phapdien_postgres_to_elasticsearch(job_id: int) -> dict[str, int]:
    """
    Đọc legal_* từ PostgreSQL, embed qua vie_embedding_v2, bulk index 3 index ES.
    """
    es = get_elasticsearch_client()
    _reset_legal_elasticsearch_indices(es)

    subject_titles, topic_titles = _load_title_lookups()

    logger.info(f"sync_phapdien_to_es job_id={job_id} indexing subjects + glossary")
    subjects_indexed = _index_subjects_with_vectors(
        es,
        topic_titles=topic_titles,
    )
    glossary_indexed = _index_glossary_with_vectors(es)

    logger.info(f"sync_phapdien_to_es job_id={job_id} indexing articles with embeddings")
    articles_indexed = _index_articles_with_vectors(
        es,
        subject_titles=subject_titles,
        topic_titles=topic_titles,
    )

    stats = {
        LEGAL_SUBJECTS_INDEX: subjects_indexed,
        LEGAL_GLOSSARY_INDEX: glossary_indexed,
        LEGAL_ARTICLES_INDEX: articles_indexed,
    }
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
