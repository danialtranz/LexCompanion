from api.apps.services.common_service import CommonService
from api.db.models import File 


class FileService(CommonService):
    model = File

   