from api.apps.services.common_service import CommonService
from api.db.models import DB, Knowledgebase


class KnowledgebaseService(CommonService):
    model = Knowledgebase

    @classmethod
    @DB.connection_context()
    def resolve_kb_for_me_upload(cls, user_id: str):
        """KB của user (created_by), permission=me, status=1. Nhiều dòng thì lấy bản mới nhất."""
        uid = str(user_id).strip()
        return (
            cls.model.select()
            .where(
                (cls.model.created_by == uid)
                & (cls.model.permission == "me")
                & (cls.model.status == "1")
            )
            .order_by(cls.model.create_time.desc())
            .first()
        )
