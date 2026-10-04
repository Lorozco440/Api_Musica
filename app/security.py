from datetime import datetime, timedelta, timezone
from typing import Annotated
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("dummy-only-for-timing-not-an-account")
bearer = HTTPBearer(auto_error=False)
Db = Annotated[Session, Depends(get_db)]


def create_token(user_id: int):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "iat": now,
                       "exp": now + timedelta(minutes=settings.access_token_minutes),
                       "iss": settings.jwt_issuer, "aud": settings.jwt_audience},
                      settings.jwt_secret, algorithm="HS256")


def current_user(db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    error = HTTPException(401, "Token ausente, inválido o vencido", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise error
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"],
                             issuer=settings.jwt_issuer, audience=settings.jwt_audience,
                             options={"require": ["sub", "exp", "iat", "iss", "aud"]})
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise error from None
    user = db.get(User, user_id)
    if user is None:
        raise error
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def admin_user(user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(403, "Se requiere el rol de administrador")
    return user


Admin = Annotated[User, Depends(admin_user)]
