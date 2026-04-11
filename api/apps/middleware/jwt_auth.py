"""JWT Bearer authentication for FastAPI routes.

Dùng như dependency trên route: đọc Authorization Bearer, verify HS256 với JWT_SECRET_KEY,
kiểm tra user tồn tại trong bảng users. Request gốc không bị đổi; controller vẫn nhận Request bình thường.
"""

from __future__ import annotations

import os
from pathlib import Path
try:
    from typing import Annotated
except ImportError:  # Python < 3.9
    from typing_extensions import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.apps.services.user_service import UserService
from api.db.models import Users
### import logger và khởi tạo 
from api.utils.logger import setup_logging
logger = setup_logging()
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

security = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET_KEY", "lex_companion_default_secret")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Users:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id") or payload.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("jwt_auth: querying user in DB user_id=%s", user_id)
    user = UserService.get_or_none(id=user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or no longer valid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUser = Annotated[Users, Depends(get_current_user)]
