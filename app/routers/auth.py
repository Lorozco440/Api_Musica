from fastapi import APIRouter, Depends
from sqlalchemy import select
from .. import schemas as s
from ..config import settings
from ..models import User
from ..rate_limit import limiter
from ..security import Db, CurrentUser, password_hasher, DUMMY_HASH, create_token
from ..services import save
from fastapi import HTTPException

router = APIRouter(tags=["Usuarios y autenticación"])


@router.post("/auth/register", response_model=s.UserOut, status_code=201, dependencies=[Depends(limiter.check)])
def register(data: s.Register, db: Db):
    return save(db, User(name=data.name, email=str(data.email).lower(),
                         password_hash=password_hasher.hash(data.password), role="client"))


@router.post("/auth/login", response_model=s.TokenOut, dependencies=[Depends(limiter.check)])
def login(data: s.Login, db: Db):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = password_hasher.verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Credenciales incorrectas", headers={"WWW-Authenticate": "Bearer"})
    return s.TokenOut(access_token=create_token(user.id), expires_in=settings.access_token_minutes * 60)


@router.get("/users/me", response_model=s.UserOut)
def profile(user: CurrentUser):
    return user


@router.patch("/users/me", response_model=s.UserOut)
def update_profile(data: s.ProfileUpdate, user: CurrentUser, db: Db):
    user.name = data.name
    return save(db, user)
