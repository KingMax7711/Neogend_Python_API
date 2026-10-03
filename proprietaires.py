from datetime import date
from database import SessionLocal
from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ConfigDict
from typing import Annotated, List
from models import Proprietaires, fnpc, fpr
import models
from auth import get_current_user
from log import api_log

def connection_required(current_user: Annotated[models.Users, Depends(get_current_user)]):
    can_use = ["admin", "owner"]
    if not current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if current_user.privileges not in can_use:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

router = APIRouter(
    prefix="/proprietaires",
    tags=["proprietaires"],
    dependencies=[Depends(connection_required)]
)
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

class proprietaireCreate(BaseModel):
    nom_famille: str
    nom_usage: str
    prenom: str
    second_prenom: str
    date_naissance: str
    sexe: str
    lieu_naissance: str
    departement_naissance_numero: int
    adresse_numero: int
    adresse_type_voie: str
    adresse_nom_voie: str
    adresse_code_postal: str
    adresse_commune: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

@router.get("/read/", response_model=List[proprietairePublic])
async def read_all_proprietaires(db: db_dependency, user: user_dependency, request: Request):
    proprietaires = db.query(Proprietaires).all()
    api_log("proprietaires.read_all", level="INFO", request=request,email=user.email, user_id=user.id, tags=["proprietaires", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return proprietaires

@router.get("/read/{proprietaire_id}/", response_model=proprietairePublic)
async def read_proprietaire(proprietaire_id: int, db: db_dependency, user: user_dependency, request: Request):
    proprietaire = db.query(Proprietaires).filter(Proprietaires.id == proprietaire_id).first()
    if not proprietaire:
        raise HTTPException(status_code=404, detail="Proprietaire not found")
    api_log("proprietaires.read_one", level="INFO", request=request,email=user.email, user_id=user.id, tags=["proprietaires", "detail"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return proprietaire

@router.post("/create/", response_model=proprietairePublic)
async def create_proprietaire(proprietaire: proprietaireCreate, db: db_dependency, user: user_dependency, request: Request):
    db_proprietaire = Proprietaires(
        nom_famille=proprietaire.nom_famille,
        nom_usage=proprietaire.nom_usage,
        prenom=proprietaire.prenom,
        second_prenom=proprietaire.second_prenom,
        date_naissance=proprietaire.date_naissance,
        sexe=proprietaire.sexe,
        lieu_naissance=proprietaire.lieu_naissance,
        departement_naissance_numero=proprietaire.departement_naissance_numero,
        adresse_numero=proprietaire.adresse_numero,
        adresse_type_voie=proprietaire.adresse_type_voie,
        adresse_nom_voie=proprietaire.adresse_nom_voie,
        adresse_code_postal=proprietaire.adresse_code_postal,
        adresse_commune=proprietaire.adresse_commune
    )
    db.add(db_proprietaire)
    db.commit()
    db.refresh(db_proprietaire)
    api_log("proprietaires.create", level="INFO", request=request,email=user.email, user_id=user.id, tags=["proprietaires", "create"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return db_proprietaire

@router.put("/update/{proprietaire_id}/", response_model=proprietairePublic)
async def update_proprietaire(proprietaire_id: int, proprietaire_update: proprietaireCreate, db: db_dependency, user: user_dependency, request: Request):
    proprietaire = db.query(Proprietaires).filter(Proprietaires.id == proprietaire_id).first()
    if not proprietaire:
        raise HTTPException(status_code=404, detail="Proprietaire not found")
    
    # Capable of partial updates
    update_data = proprietaire_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(proprietaire, field, value)
    
    db.commit()
    db.refresh(proprietaire)
    api_log("proprietaires.update", level="INFO", request=request,email=user.email, user_id=user.id, tags=["proprietaires", "update"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return proprietaire

@router.get("/dependents/{proprietaire_id}/")
async def proprietaire_dependents(proprietaire_id: int, db: db_dependency, user: user_dependency):
    if not db.query(Proprietaires.id).filter(Proprietaires.id == proprietaire_id).first():
        raise HTTPException(status_code=404, detail="Proprietaire not found")
    fnpcs = db.query(fnpc).filter(fnpc.prop_id == proprietaire_id).all()
    nephs = [f.neph for f in fnpcs]
    infractions = db.query(models.infractions_routieres).filter(models.infractions_routieres.neph.in_(nephs)).all() if nephs else []
    fprs = db.query(fpr).filter(fpr.prop_id == proprietaire_id).all()
    fprs_detached = db.query(fpr).filter(fpr.neph.in_(nephs), fpr.prop_id.is_distinct_from(proprietaire_id)).all() if nephs else []
    sivs = db.query(models.siv).filter(models.siv.prop_id == proprietaire_id).all()
    sivs_detached = db.query(models.siv).filter(models.siv.co_prop_id == proprietaire_id).all()
    return {
        "deleted": {
            "FNPC": [f"FNPC #{f.id} - NEPH {f.neph}" for f in fnpcs],
            "Infractions": [f"Infraction #{i.id} - {i.classe} ({i.date_infraction})" for i in infractions],
            "FPR": [{"label": f"FPR #{r.id}", "motif": r.motif_enregistrement} for r in fprs],
            "SIV": [f"SIV #{s.id} - {s.ci_numero_immatriculation or 'sans immatriculation'}" for s in sivs],
        },
        "detached": {
            "FPR d'autres propriétaires (lien FNPC retiré)": [{"label": f"FPR #{r.id}", "motif": r.motif_enregistrement} for r in fprs_detached],
            "SIV où il est co-propriétaire (co-propriétaire retiré)": [f"SIV #{s.id} - {s.ci_numero_immatriculation or 'sans immatriculation'}" for s in sivs_detached],
        },
    }

@router.delete("/delete/{proprietaire_id}/")
async def delete_proprietaire(proprietaire_id: int, db: db_dependency, user: user_dependency, request: Request):
    proprietaire = db.query(Proprietaires).filter(Proprietaires.id == proprietaire_id).first()
    if not proprietaire:
        raise HTTPException(status_code=404, detail="Proprietaire not found")

    try:
        nephs = [n for (n,) in db.query(fnpc.neph).filter(fnpc.prop_id == proprietaire_id).all()]
        if nephs:
            db.query(models.infractions_routieres).filter(models.infractions_routieres.neph.in_(nephs)).delete(synchronize_session=False)
            # Tous les FPR liés à ces FNPC sont détachés (prop_id peut être NULL, donc pas de filtre dessus)
            db.query(fpr).filter(fpr.neph.in_(nephs)).update({fpr.neph: None}, synchronize_session=False)
        db.query(fpr).filter(fpr.prop_id == proprietaire_id).delete(synchronize_session=False)
        db.query(models.siv).filter(models.siv.prop_id == proprietaire_id).delete(synchronize_session=False)
        db.query(models.siv).filter(models.siv.co_prop_id == proprietaire_id).update({models.siv.co_prop_id: None}, synchronize_session=False)
        db.query(fnpc).filter(fnpc.prop_id == proprietaire_id).delete(synchronize_session=False)
        db.delete(proprietaire)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Suppression impossible : des éléments liés existent encore")
    api_log("proprietaires.delete", level="INFO", request=request,email=user.email, user_id=user.id, tags=["proprietaires", "delete"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "Proprietaire deleted successfully"}