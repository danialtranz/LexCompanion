import json
import os
import urllib.parse
import urllib.error
import urllib.request

from datetime import datetime, timedelta, timezone
from pathlib import Path
## import get_uuid 
from api.utils.utils import get_uuid
import jwt
from dotenv import load_dotenv
from fastapi import HTTPException

from api.apps.services.user_2tenant_2usertenant_service import UserService, TenantService, UserTenantService
from api.apps.services.kb_service import KnowledgebaseService
load_dotenv(Path(__file__).resolve().parents[3] / ".env")
### khoi tao log trong controller
from api.utils.logger import setup_logging
logger = setup_logging()

def _post_form(url: str, payload: dict):
    encoded_data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=encoded_data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="ignore")
        try:
            error_json = json.loads(response_body) if response_body else {}
            error_msg = (
                error_json.get("error_description")
                or error_json.get("error")
                or "Google OAuth token exchange failed"
            )
        except json.JSONDecodeError:
            error_msg = response_body or "Google OAuth token exchange failed"
        raise HTTPException(status_code=400, detail=error_msg)
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=502, detail=f"Google OAuth connection failed: {exc.reason}"
        )


def _get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="ignore")
        try:
            error_json = json.loads(response_body) if response_body else {}
            error_msg = (
                error_json.get("error_description")
                or error_json.get("error")
                or "Cannot fetch Google profile"
            )
        except json.JSONDecodeError:
            error_msg = response_body or "Cannot fetch Google profile"
        raise HTTPException(status_code=400, detail=error_msg)
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=502, detail=f"Google profile connection failed: {exc.reason}"
        )


def _exchange_google_code(code: str, google_redirect_uri: str):
    token_payload = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uri": google_redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", ""),
        "grant_type": "authorization_code",
    }
    token_result = _post_form("https://oauth2.googleapis.com/token", token_payload)
    access_token = token_result.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Cannot get access_token from Google OAuth")
    return access_token


def _resolve_role(user) -> str:
    if user.status == "banned":
        return "banned"
    if user.super_admin:
        return "super_admin"
    return "user"


def _sign_jwt(user_id: str, role: str) -> str:
    secret_key = os.getenv("JWT_SECRET_KEY", "lex_companion_default_secret")
    expires_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def oauth_login(code: str, google_redirect_uri: str):
    try:
        logger.info("oauth_login started")
        if not code:
            logger.info("oauth_login missing code")
            raise HTTPException(status_code=400, detail="code is required")

        
        access_token = _exchange_google_code(code, google_redirect_uri)
        logger.info("oauth_login exchange token success")

        
        google_profile = _get_json(
            f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
        )
        email = google_profile.get("email")
        username = google_profile.get("name") or google_profile.get("email", "").split("@")[0]
        avatar = google_profile.get("picture")
        logger.info(f"oauth_login profile fetched email={email}")
        if not email:
            logger.info("oauth_login Google profile has no email")
            
            raise HTTPException(status_code=400, detail="Google account has no email")

        logger.info(f"oauth_login checking user by email={email}")
        user = UserService.get_by_email(email=email)
        user_state = "old_user"
        if not user:
            logger.info(f"oauth_login creating new user email={email}")
            is_first_user = UserService.get_all().count() == 0
            user = UserService.save(
                id=get_uuid(),
                email=email,
                username=username,
                password=None,
                super_admin=is_first_user,
                status="1",
            )
            logger.info(
                f"oauth_login created user user_id={user.id}, super_admin={user.super_admin}"
            )
            user_state = "new_user"
            ####### tao tenant moi cho user , va tao 1 row trong UserTenent de user nay lam admin cua chinh ho luon 
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
            ### roi sau do tao 1 kb cho ho luon 
            KnowledgebaseService.save(
                id=get_uuid(),
                name=f"{user.username}'s default Knowledge Base",
                tenant_id=tenant.id,
                created_by=user.id,
                status="1",
                language="vietnamese",
                permission="me",
                similarity_threshold=0.2,
                vector_size=1024,
                doc_num=0,
                token_num=0,
                chunk_num=0,
            )
        else:
            logger.info(f"oauth_login existing user found user_id={user.id}")

        role = _resolve_role(user)
        
        token = _sign_jwt(user_id=user.id, role=role)
        
        return {
            "code": 0,
            "msg": "OAuth login success",
            "data": {
                "token": token,
                "role": role,
                "user_state": user_state,
                "avatar": avatar,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "password": user.password,
                    "super_admin": user.super_admin,
                    "status": user.status,
                    "create_date": user.create_date.isoformat() if user.create_date else None,
                    "update_date": user.update_date.isoformat() if user.update_date else None,
                },
            },
        }
    except HTTPException as exc:
        logger.error(f"oauth_login HTTPException: {exc.detail}")
        return {
            "msg": str(exc.detail),
            "code": exc.status_code,
            "data": None,
        }
    except Exception as e:
        logger.error(f"Error in oauth_login: {e}")
        return {
            "msg": str(e),
            "code": 500,
            "data": None,
        }
