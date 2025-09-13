from datetime import date
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, ConfigDict
from typing import List, Annotated
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
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
from auth import get_current_user

load_dotenv()

app = FastAPI()
app.title = "Neogend API"
app.version = str(os.getenv("APP_VERSION", "Unknown"))
START_TIME = time.time()
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(connected.router)

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

# Exécuter create_all uniquement hors production, sauf si DB_BOOTSTRAP=true
IS_PROD = os.getenv("APP_RELEASE_STATUS", "").lower() == "prod"
DB_BOOTSTRAP = os.getenv("DB_BOOTSTRAP", "").lower() == "true"
if DB_BOOTSTRAP:
    models.Base.metadata.create_all(bind=engine)

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

@app.get("/users/me/", response_model=UserPublic)
async def read_user_me(current_user: user_dependency):
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return current_user

@app.get("/health")
async def health(db: db_dependency):
    uptime_s = round(time.time() - START_TIME, 3)
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "db_health": "ok" if db_ok else "degraded",
        "api_version": app.version + str(' (' + os.getenv("APP_RELEASE_STATUS", "Unknown") + ')'),
        "uptime_seconds": uptime_s,
    }