from fastapi import APIRouter
from pydantic import BaseModel

from api.apps.controllers.user_controller import oauth_login

router = APIRouter(prefix="/v1/user", tags=["user"])


class OAuthLoginRequest(BaseModel):
    code: str
    google_redirect_uri: str = ""


@router.post("/oAuth-login")
def oauth_login_api(payload: OAuthLoginRequest):
    return oauth_login(code=payload.code, google_redirect_uri=payload.google_redirect_uri)
