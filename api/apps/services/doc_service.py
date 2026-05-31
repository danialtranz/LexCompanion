from api.apps.services.common_service import CommonService
from api.db.models import DB, Document


class DocumentService(CommonService):
    model = Document

    @classmethod
    @DB.connection_context()
    def get_active_by_id_and_owner(cls, doc_id: str, owner_id: str) -> Document | None:
        """Document đang active (status=1) và thuộc owner."""
        return cls.model.get_or_none(
            (cls.model.id == doc_id)
            & (cls.model.status == "1")
            & (cls.model.created_by == owner_id)
        )

    @classmethod
    @DB.connection_context()
    def list_active_by_kb_id(cls, kb_id: str, page: int, page_size: int):
        """Document status=1 thuộc kb_id, phân trang; create_time giảm dần."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        q = (
            cls.model.select()
            .where((cls.model.kb_id == kb_id) & (cls.model.status == "1"))
            .order_by(cls.model.create_time.desc())
        )
        total = q.count()
        rows = list(q.paginate(page, page_size))
        return total, rows

    @classmethod
    @DB.connection_context()
    def mark_parse_queued(cls, doc_id: str) -> int:
        """Đánh dấu document đã được đưa vào hàng đợi parse (run=1)."""
        return cls.update_by_id(doc_id, {"run": "1"})

    @classmethod
    @DB.connection_context()
    def get_active_by_kb_and_content_hash(
        cls, kb_id: str, content_hash: str
    ) -> Document | None:
        """Document active trong KB đã có cùng content_hash (tránh import trùng)."""
        if not content_hash:
            return None
        return cls.model.get_or_none(
            (cls.model.kb_id == kb_id)
            & (cls.model.status == "1")
            & (cls.model.content_hash == content_hash)
        )
