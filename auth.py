from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from database import SessionLocal
from models import Users
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from dotenv import load_dotenv
import os
from log import api_log
from typing import Literal, cast

load_dotenv()

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

SECRET_KEY = str(os.getenv("SECRET_KEY"))
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Cookies config
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
_raw_samesite = os.getenv("COOKIE_SAMESITE", "none" if COOKIE_SECURE else "lax").lower()
CookieSameSite = Literal['lax', 'strict', 'none']
if _raw_samesite not in ("lax", "strict", "none"):
    _raw_samesite = "none" if COOKIE_SECURE else "lax"
COOKIE_SAMESITE: CookieSameSite = cast(CookieSameSite, _raw_samesite)

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")


class Token(BaseModel):
    access_token: str
    token_type: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

# ---------- utils tokens ----------
def _create_token(payload: dict, expires_delta: timedelta) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(nipol: str, user_id: int, token_version: int) -> str:
    return _create_token({"sub": nipol, "id": user_id, "ver": token_version}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

def create_refresh_token(nipol: str, user_id: int, token_version: int) -> str:
    return _create_token({"sub": nipol, "id": user_id, "ver": token_version}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

def authenticate_user(nipol: str, password: str, db: Session):
    user = db.query(Users).filter(Users.rp_nipol == nipol).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.password): # type: ignore
        return False
    return user

# ---------- Login ----------
@router.post("/token", response_model=Token)
async def login_for_acces_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency, request: Request):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        api_log("login.failed", level="INFO", request=request, tags=["auth", "login"], email=form_data.username, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(user.rp_nipol, user.id, user.token_version) # type: ignore
    refresh_token = create_refresh_token(user.rp_nipol, user.id, user.token_version) # type: ignore

    resp = JSONResponse({
        "access_token": access_token,
        "token_type": "bearer"
    })

    resp.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,  # "none" exige HTTPS côté navigateur
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/",
    )
    api_log("login.success", level="INFO", request=request, tags=["auth", "login"], user_id=user.id,email=user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return resp

# ---------- refresh: lit le cookie, renvoie un NOUVEL access ----------
@router.post("/refresh", response_model=Token)
async def refresh_access_token(request: Request, db: db_dependency):
    rt = request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        payload = jwt.decode(rt, SECRET_KEY, algorithms=[ALGORITHM])
        nipol = payload.get("sub")
        user_id = payload.get("id")
        ver = payload.get("ver")
        if not nipol or not user_id:
            raise JWTError("invalid payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(Users).filter(Users.id == user_id, Users.rp_nipol == nipol).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found for refresh")

    # Vérifier la version stockée
    if ver is None or ver != user.token_version:  # type: ignore
        raise HTTPException(status_code=403, detail="Refresh token invalidated")

    new_access = create_access_token(user.rp_nipol, user.id, user.token_version) # type: ignore
    api_log("token.refresh", level="INFO", request=request, tags=["auth", "refresh"], user_id=user.id,email=user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"access_token": new_access, "token_type": "bearer"}

# ---------- logout: supprime le cookie ----------
@router.post("/logout")
async def logout():
    resp = JSONResponse({"message": "logged out"})
    resp.delete_cookie("refresh_token", path="/")
    return resp

# ---------- get_current_user : Lit l'acces Token et renvoie l'utilisateur ----------
async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)], db: db_dependency):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nipol: str = payload.get("sub") # type: ignore
        user_id: int = payload.get("id") # type: ignore
        ver: int | None = payload.get("ver") # type: ignore
        if nipol is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(Users).filter(Users.rp_nipol == nipol, Users.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Optionnel : vérifier version pour les access tokens si on veut force logout global
    if ver is not None and ver != user.token_version:  # type: ignore
        raise HTTPException(status_code=403, detail="Token version invalidated")
    return user
