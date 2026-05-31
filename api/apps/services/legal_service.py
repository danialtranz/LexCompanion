from datetime import datetime

from api.apps.services.common_service import CommonService
from api.db.models import (
    DB,
    LegalArticle,
    LegalGlossary,
    LegalIngestionJob,
    LegalOntologySubject,
    LegalSubject,
    LegalTopic,
    LegalTreeNode,
)


class LegalTopicService(CommonService):
    model = LegalTopic

    @classmethod
    @DB.connection_context()
    def get_by_topic_id(cls, topic_id: str):
        topic_id = (topic_id or "").strip()
        if not topic_id:
            return None
        return cls.get_or_none(topic_id=topic_id)


class LegalSubjectService(CommonService):
    model = LegalSubject

    @classmethod
    @DB.connection_context()
    def get_by_subject_id(cls, subject_id: str):
        subject_id = (subject_id or "").strip()
        if not subject_id:
            return None
        return cls.get_or_none(subject_id=subject_id)


class LegalTreeNodeService(CommonService):
    model = LegalTreeNode

    _TOPIC_LIST_COLS = (
        LegalTreeNode.id,
        LegalTreeNode.node_id,
        LegalTreeNode.parent_id,
        LegalTreeNode.kind,
        LegalTreeNode.number,
        LegalTreeNode.title,
        LegalTreeNode.created_at,
        LegalTreeNode.updated_at,
    )

    @classmethod
    @DB.connection_context()
    def list_top_level_topics_paginated(cls, page: int, page_size: int):
        """Phân trang topic gốc từ legal_tree_nodes (kind=topic, parent_id='null')."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        q = (
            cls.model.select(*cls._TOPIC_LIST_COLS)
            .where(
                (cls.model.kind == "topic") & (cls.model.parent_id == None)
            )
            .order_by(cls.model.number.asc(), cls.model.id.asc())
        )
        total = q.count()
        rows = list(q.paginate(page, page_size))
        return total, rows

    @classmethod
    @DB.connection_context()
    def list_subjects_by_topic_paginated(cls, topic_id: str, page: int, page_size: int):
        """Phân trang subject con của topic từ legal_tree_nodes."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        q = (
            cls.model.select(*cls._TOPIC_LIST_COLS)
            .where(
                (cls.model.kind == "subject") & (cls.model.parent_id == topic_id)
            )
            .order_by(cls.model.number.asc(), cls.model.id.asc())
        )
        total = q.count()
        rows = list(q.paginate(page, page_size))
        return total, rows


class LegalArticleService(CommonService):
    model = LegalArticle

    @classmethod
    @DB.connection_context()
    def list_by_subject_paginated(cls, subject_id: str, page: int, page_size: int):
        """Phân trang legal_articles theo subject_id."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        q = (
            cls.model.select()
            .where(cls.model.subject_id == subject_id)
            .order_by(cls.model.id.asc())
        )
        total = q.count()
        rows = list(q.paginate(page, page_size))
        return total, rows


class LegalOntologySubjectService(CommonService):
    model = LegalOntologySubject


class LegalGlossaryService(CommonService):
    model = LegalGlossary


class LegalIngestionJobService(CommonService):
    model = LegalIngestionJob

    @classmethod
    @DB.connection_context()
    def get_latest_completed_job(cls, dataset_name: str):
        return (
            cls.model.select()
            .where(
                (cls.model.dataset_name == dataset_name)
                & (cls.model.status == "completed")
            )
            .order_by(cls.model.id.desc())
            .first()
        )

    @classmethod
    @DB.connection_context()
    def get_running_job(cls, dataset_name: str, dataset_version: str | None = None):
        query = cls.model.select().where(
            (cls.model.dataset_name == dataset_name) & (cls.model.status == "running")
        )
        if dataset_version is not None:
            query = query.where(cls.model.dataset_version == dataset_version)
        return query.order_by(cls.model.id.desc()).first()

    @classmethod
    @DB.connection_context()
    def create_running(cls, *, dataset_name: str, dataset_version: str | None = None):
        return cls.model.create(
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            status="running",
            started_at=datetime.utcnow(),
        )

    @classmethod
    @DB.connection_context()
    def mark_finished(
        cls,
        job_id: int,
        *,
        status: str,
        total_rows: int | None = None,
        success_rows: int | None = None,
        failed_rows: int | None = None,
        error_message: str | None = None,
    ) -> None:
        cls.model.update(
            status=status,
            finished_at=datetime.utcnow(),
            total_rows=total_rows,
            success_rows=success_rows,
            failed_rows=failed_rows,
            error_message=error_message,
        ).where(cls.model.id == job_id).execute()

    @classmethod
    @DB.connection_context()
    def update_progress(
        cls,
        job_id: int,
        *,
        success_rows: int,
        failed_rows: int,
    ) -> None:
        cls.model.update(
            success_rows=success_rows,
            failed_rows=failed_rows,
        ).where(cls.model.id == job_id).execute()
