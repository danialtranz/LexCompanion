from api.apps.services.common_service import CommonService
from api.apps.services.user_2tenant_2usertenant_service import (
    TenantService,
    UserTenantService,
)
from api.db.models import DB, Knowledgebase, Users
from api.utils.utils import get_uuid


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

    @classmethod
    @DB.connection_context()
    def ensure_kb_for_super_admin(cls, user: Users) -> Knowledgebase:
        """KB permission=me cho super_admin; tạo tenant + KB nếu chưa có."""
        kb = cls.resolve_kb_for_me_upload(user.id)
        if kb:
            return kb

        ut = (
            UserTenantService.model.select()
            .where(
                (UserTenantService.model.user_id == user.id)
                & (UserTenantService.model.status == "1")
            )
            .order_by(UserTenantService.model.create_time.desc())
            .first()
        )
        if ut:
            tenant_id = ut.tenant_id
        else:
            tenant = TenantService.save(
                id=get_uuid(),
                name=f"{user.username}'s Tenant",
                status="1",
            )
            UserTenantService.save(
                id=get_uuid(),
                user_id=user.id,
                tenant_id=tenant.id,
                role="admin",
                invited_by=user.id,
                status="1",
            )
            tenant_id = tenant.id

        return cls.save(
            id=get_uuid(),
            name=f"{user.username}'s default Knowledge Base",
            tenant_id=tenant_id,
            created_by=user.id,
            status="1",
            language="vietnamese",
            permission="me",
            similarity_threshold=0.2,
            vector_size=0,
            doc_num=0,
            token_num=0,
            chunk_num=0,
        )
