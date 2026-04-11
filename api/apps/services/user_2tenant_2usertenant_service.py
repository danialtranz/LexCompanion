from api.apps.services.common_service import CommonService
from api.db.models import Users, UserTenant, Tenant 


class UserService(CommonService):
    model = Users

    @classmethod
    def get_by_email(cls, email: str):
        return cls.get_or_none(email=email)




class UserTenantService(CommonService):
    model = UserTenant

   

class TenantService(CommonService):
    model = Tenant



