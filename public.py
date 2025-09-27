from datetime import date
from database import SessionLocal
from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Body, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Annotated, List
from models import Proprietaires  # Add this import for the Users model
import models
from auth import get_current_user
from log import api_log

def connection_required(current_user: Annotated[models.Users, Depends(get_current_user)]):
    can_see = ["opj", "apj", "apja"]
    if not current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if current_user.rp_qualif not in can_see:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

router = APIRouter(
    prefix="/public",
    tags=["public"],
    dependencies=[Depends(connection_required)]
)

class infractionPublic(BaseModel):
    id: int
    article: str | None = None
    classe: str | None = None
    natinf: str | None = None
    points: int | None = None
    nipol: str | None = None
    date_infraction: date | None = None
    details: str | None = None
    statut: str | None = None
    neph: int | None = None
    model_config = ConfigDict(from_attributes=True)

class proprietairePublic(BaseModel):
    id: int
    nom_famille: str
    nom_usage: str
    prenom: str
    second_prenom: str
    date_naissance: date
    sexe: str
    lieu_naissance: str
    departement_naissance_numero: int
    adresse_numero: int
    adresse_type_voie: str
    adresse_nom_voie: str
    adresse_code_postal: str
    adresse_commune: str

class fnpcPublic(BaseModel):

    id: int
    neph: int
    numero_titre: int
    date_delivrance: date
    prefecture_delivrance: str
    date_expiration: date
    statut: str
    validite: str

    cat_am: bool
    cat_am_delivrance: date | None = None
    cat_a1: bool
    cat_a1_delivrance: date | None = None
    cat_a2: bool
    cat_a2_delivrance: date | None = None
    cat_a: bool
    cat_a_delivrance: date | None = None
    cat_b1: bool
    cat_b1_delivrance: date | None = None
    cat_b: bool
    cat_b_delivrance: date | None = None
    cat_c1: bool
    cat_c1_delivrance: date | None = None
    cat_c: bool
    cat_c_delivrance: date | None = None
    cat_d1: bool
    cat_d1_delivrance: date | None = None
    cat_d: bool
    cat_d_delivrance: date | None = None
    cat_be: bool
    cat_be_delivrance: date | None = None
    cat_c1e: bool
    cat_c1e_delivrance: date | None = None
    cat_ce: bool
    cat_ce_delivrance: date | None = None
    cat_d1e: bool
    cat_d1e_delivrance: date | None = None
    cat_de: bool
    cat_de_delivrance: date | None = None

    code_restriction: str | None = None
    probatoire: bool
    date_probatoire: date | None = None
    points: int

    prop_id: int

    model_config = ConfigDict(from_attributes=True)

class fprPublic(BaseModel):
    id: int
    exactitude: str | None = None  # Identité confirmée, non confirmée, usurpée

    date_enregistrement: date
    motif_enregistrement: str | None = None
    autorite_enregistrement: str | None = None
    lieu_faits: str | None = None
    details: str | None = None

    dangerosite: str | None = None  # Faible, moyenne, élevée
    signes_distinctifs: str | None = None

    conduite: str | None = None  # Conduite à tenir en cas de découverte

    # Clés étrangères / associations
    prop_id: int
    neph: int | None = None  # BIGINT côté DB
    num_fijait: int | None = None  # BIGINT côté DB

    model_config = ConfigDict(from_attributes=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

@router.get("/infractions/read/", response_model=List[infractionPublic])
async def read_all_infractions(db: db_dependency, user: user_dependency, request: Request):
    infractions = db.query(models.infractions_routieres).all()
    api_log("infractions.read_all", level="INFO", request=request,email=user.email, user_id=user.id, tags=["infractions", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return infractions

@router.get("/infractions/read/{infraction_id}/", response_model=infractionPublic)
async def read_infraction(infraction_id: int, db: db_dependency, user: user_dependency, request: Request):
    infraction = db.query(models.infractions_routieres).filter(models.infractions_routieres.id == infraction_id).first()
    if not infraction:
        raise HTTPException(status_code=404, detail="Infraction not found")
    api_log("infractions.read_one", level="INFO", request=request,email=user.email, user_id=user.id, tags=["infractions", "detail"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return infraction

@router.get("/infractions/read/by_neph/{neph}/", response_model=List[infractionPublic])
async def read_infractions_by_neph(neph: int, db: db_dependency, user: user_dependency, request: Request):
    infractions = db.query(models.infractions_routieres).filter(models.infractions_routieres.neph == neph).all()
    api_log("infractions.read_by_neph", level="INFO", request=request,email=user.email, user_id=user.id, tags=["infractions", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return infractions

@router.get("/proprietaires/read/", response_model=List[proprietairePublic])
async def read_all_proprietaires(db: db_dependency, user: user_dependency, request: Request):
    proprietaires = db.query(Proprietaires).all()
    api_log("proprietaires.read_all", level="INFO", request=request,email=user.email, user_id=user.id, tags=["proprietaires", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return proprietaires

@router.get("/proprietaires/read/{proprietaire_id}/", response_model=proprietairePublic)
async def read_proprietaire(proprietaire_id: int, db: db_dependency, user: user_dependency, request: Request):
    proprietaire = db.query(Proprietaires).filter(Proprietaires.id == proprietaire_id).first()
    if not proprietaire:
        raise HTTPException(status_code=404, detail="Proprietaire not found")
    api_log("proprietaires.read_one", level="INFO", request=request,email=user.email, user_id=user.id, tags=["proprietaires", "detail"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return proprietaire

@router.get("/fnpc/read/", response_model=List[fnpcPublic])
async def read_all_fnpcs(db: db_dependency, user: user_dependency, request: Request):
    fnpcs = db.query(models.fnpc).all()
    api_log("fnpc.read_all", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fnpc", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return fnpcs

@router.get("/fnpc/read/{fnpc_id}/", response_model=fnpcPublic)
async def read_fnpc(fnpc_id: int, db: db_dependency, user: user_dependency, request: Request):
    fnpc = db.query(models.fnpc).filter(models.fnpc.id == fnpc_id).first()
    if not fnpc:
        raise HTTPException(status_code=404, detail="fnpc not found")
    api_log("fnpc.read", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fnpc", "read"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return fnpc

@router.get("/fpr/read/", response_model=List[fprPublic])
async def read_all_fpr(db: db_dependency, user: user_dependency, request: Request):
    fpr_records = db.query(models.fpr).all()
    api_log("fpr.read_all", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fpr", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return fpr_records

@router.get("/fpr/read/{fpr_id}/", response_model=fprPublic)
async def read_fpr(fpr_id: int, db: db_dependency, user: user_dependency, request: Request):
    fpr_record = db.query(models.fpr).filter(models.fpr.id == fpr_id).first()
    if not fpr_record:
        raise HTTPException(status_code=404, detail="FPR not found")
    api_log("fpr.read_one", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fpr", "detail"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return fpr_record