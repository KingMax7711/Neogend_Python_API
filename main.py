from datetime import date
from fastapi import FastAPI, HTTPException, Depends, status, Request
from pydantic import BaseModel, ConfigDict
from typing import List, Annotated, Optional, cast
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import time
import os
from dotenv import load_dotenv
# Local
from database import engine, SessionLocal
from models import Users
import models
import auth
import admin
import connected
import proprietaires
import fnpc
import infractions
import fpr
import siv

import public
from auth import get_current_user
from log import api_log

load_dotenv()

app = FastAPI(
    # Permet d’être servi derrière un préfixe (ex: /api) via le reverse proxy
    root_path=os.getenv("API_ROOT_PATH", "/api"),
)
app.title = "Neogend API"
app.version = str(os.getenv("APP_VERSION", "Unknown"))
START_TIME = time.time()
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(connected.router)
app.include_router(proprietaires.router)
app.include_router(fnpc.router)
app.include_router(infractions.router)
app.include_router(fpr.router)
app.include_router(siv.router)

app.include_router(public.router)


# Détermine dynamiquement les origines CORS autorisées
_frontend_origins_env = os.getenv("FRONTEND_ORIGINS", "")
if _frontend_origins_env:
    _allowed_origins = [o.strip() for o in _frontend_origins_env.split(",") if o.strip()]
else:
    # Valeurs par défaut utiles en dev: Vite (5173) et dev server (3000)
    _allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://192.168.1.40:3000",
        "https://192.168.1.40:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def _on_startup() -> None:
    # Force l'initialisation du logger et la création du répertoire logs
    api_log("app.startup", level="INFO", data={"version": app.version})
    # Créer un admin par défaut si la base est vide
    try:
        create_default_admin_user()
    except Exception as e:
        api_log("app.startup.default_admin.failed", level="ERROR", data={"error": str(e)})

# Exécuter create_all uniquement hors production, sauf si DB_BOOTSTRAP=true
IS_PROD = os.getenv("APP_RELEASE_STATUS", "").lower() == "prod"
DB_BOOTSTRAP = os.getenv("DB_BOOTSTRAP", "").lower() == "true"
if DB_BOOTSTRAP:
    models.Base.metadata.create_all(bind=engine)


bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserBase(BaseModel):
    # Common fields
    id: int
    first_name: str
    last_name: str
    email: str
    password: str
    discord_id: str | None = None
    inscription_date: date | None = None
    inscription_status: str | None = None  # valid / pending / denied
    # RP Information
    rp_first_name: str | None = None
    rp_last_name: str | None = None
    rp_birthdate: date | None = None  # Utilisez date si vous voulez une conversion automatique
    rp_gender: str | None = None
    rp_grade: str | None = None
    rp_affectation: str | None = None
    rp_qualif: str | None = None
    rp_nipol: str | None = None
    rp_server: str | None = None
    rp_service: str | None = None  # Police(PN) / Gendarmerie(GN) / Police Municipale(PM)
    # Admin
    privileges: str | None = None
    model_config = ConfigDict(from_attributes=True)

class UserPublic(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    temp_password: bool
    discord_id: str | None = None
    inscription_date: date | None = None
    inscription_status: str | None = None  # valid / pending / denied
    rp_first_name: str | None = None
    rp_last_name: str | None = None
    rp_birthdate: date | None = None  # Utilisez date si vous voulez une conversion automatique
    rp_gender: str | None = None
    rp_grade: str | None = None
    rp_affectation: str | None = None
    rp_qualif: str | None = None
    rp_nipol: str | None = None
    rp_server: str | None = None
    rp_service: str | None = None  # Police(PN) / Gendarmerie(GN) / Police Municipale(PM)
    privileges: str | None = None
    model_config = ConfigDict(from_attributes=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

# Création d'un utilisateur admin par défaut si aucun utilisateur n'existe
def create_default_admin_user():
    db = SessionLocal()
    try:
        user_count = db.query(Users).count()
        if user_count == 0:
            default_admin_nipol = os.getenv("DEFAULT_ADMIN_NIPOL", "123456789")
            default_admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")
            default_admin = Users(
                first_name="admin",
                last_name="default",
                email="admin@admin.com",
                password=bcrypt_context.hash(default_admin_password),
                rp_first_name="admin",
                rp_last_name="default",
                temp_password=False,
                inscription_status="valid",
                rp_nipol=default_admin_nipol,
                privileges="owner",
            )
            db.add(default_admin)
            db.commit()
            db.refresh(default_admin)
            api_log("users.create.default_admin", level="CRITICAL", user_id=default_admin.id) # type: ignore
    finally:
        db.close()

@app.get("/users/me/", response_model=UserPublic)
async def read_user_me(current_user: user_dependency, request: Request):
    if current_user is None:
        api_log("users.me.unauthenticated", level="WARNING", request=request, tags=["users", "me"], correlation_id=request.headers.get("x-correlation-id"))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id: Optional[int] = cast(Optional[int], getattr(current_user, "id", None))
    email: Optional[str] = cast(Optional[str], getattr(current_user, "email", None))
    api_log(
        "users.me.success",
        level="INFO",
        request=request,
        user_id=user_id,
        email=email,
        tags=["users", "me"],
        correlation_id=request.headers.get("x-correlation-id"),
    )
    return current_user

@app.get("/health")
async def health(db: db_dependency, request: Request):
    uptime_s = round(time.time() - START_TIME, 3)
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
        api_log("health.check.failed", level="ERROR", request=request, correlation_id=request.headers.get("x-correlation-id"))
    return {
        "status": "ok" if db_ok else "degraded",
        "db_health": "ok" if db_ok else "degraded",
        "api_version": app.version + str(' (' + os.getenv("APP_RELEASE_STATUS", "Unknown") + ')'),
        "uptime_seconds": uptime_s,
    }