"""Parse documents from MinIO: Docling → chunk → embeddings → Elasticsearch."""

from __future__ import annotations

import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from elasticsearch.helpers import bulk
from markdownify import markdownify as md

from deepagent.core.text_splitters.law_split import LawTextSplitter, LLMResponseValidationError
from api.apps.services.doc_service import DocumentService
from api.apps.services.file_service import FileService
from api.apps.services.kb_service import KnowledgebaseService
from api.db.models import db
from api.utils.logger import setup_logging
from api.utils.minio_conn import LexCompanionMinio
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from deepagent.core.providers.embeddings.base import create_embeddings
from deepagent.core.providers.llms.base import create_chat_model
from deepagent.core.prompts.prompt import EXTRACT_LAW_REFERENCE_PROMPT
from deepagent.core.retrievers.base import build_elasticsearch_client, create_retriever
import json
from enum import Enum

logger = setup_logging()


class SourceType(Enum):
    MINIO = "minio"
    WEB_SCRAPING = "url_scraping"

class RefType(Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"

_TYPE_ALIASES = {"parse_ducument": "parse_document"}

from deepagent.core.document_loaders.docdealing import warmup_docling






def run_parse_document_job(document_id: str, parse_type: str = "docdealing") -> None:
    """Sync pipeline: load Document → MinIO → Docling → chunk → embed → ES. Updates ``progress`` on the row."""
    

    logger.info(f"run_parse_document_job: document_id={document_id} parse_type={parse_type}")


def run_import_hf_phapdien_job(job_id: int, dataset_name: str) -> None:
    """Tải dataset phapdien: PostgreSQL rồi Elasticsearch (pipeline trong task_execution)."""
    from api.worker.task_execution import run_phapdien_import_pipeline

    logger.info(f"run_import_hf_phapdien_job: job_id={job_id} dataset={dataset_name!r}")
    run_phapdien_import_pipeline(job_id, dataset_name)

def normalize_task_type(raw: str | None) -> str:
    t = (raw or "").strip().lower()
    return _TYPE_ALIASES.get(t, t)