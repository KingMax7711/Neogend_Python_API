from datetime import date
from database import SessionLocal
from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Body, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Annotated, List
from models import fpr  # Add this import for the Users model
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
    prefix="/fpr",
    tags=["fpr"],
    dependencies=[Depends(connection_required)]
)

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

class fprCreate(BaseModel):
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

class fprUpdate(BaseModel):
    exactitude: str | None = None  # Identité confirmée, non confirmée, usurpée

    date_enregistrement: date | None = None
    motif_enregistrement: str | None = None
    autorite_enregistrement: str | None = None
    lieu_faits: str | None = None
    details: str | None = None

    dangerosite: str | None = None  # Faible, moyenne, élevée
    signes_distinctifs: str | None = None

    conduite: str | None = None  # Conduite à tenir en cas de découverte

    # Clés étrangères / associations
    prop_id: int | None = None
    neph: int | None = None  # BIGINT côté DB
    num_fijait: int | None = None  # BIGINT côté DB

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

@router.get("/read/", response_model=List[fprPublic])
async def read_all_fpr(db: db_dependency, user: user_dependency, request: Request):
    fpr_records = db.query(fpr).all()
    api_log("fpr.read_all", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fpr", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return fpr_records

@router.get("/read/{fpr_id}/", response_model=fprPublic)
async def read_fpr(fpr_id: int, db: db_dependency, user: user_dependency, request: Request):
    fpr_record = db.query(fpr).filter(fpr.id == fpr_id).first()
    if not fpr_record:
        raise HTTPException(status_code=404, detail="FPR not found")
    api_log("fpr.read_one", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fpr", "detail"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return fpr_record

@router.post("/create/", response_model=fprPublic)
async def create_fpr(fpr_data: fprCreate, db: db_dependency, user: user_dependency, request: Request):
    db_fpr = fpr(
        exactitude=fpr_data.exactitude,
        date_enregistrement=fpr_data.date_enregistrement,
        motif_enregistrement=fpr_data.motif_enregistrement,
        autorite_enregistrement=fpr_data.autorite_enregistrement,
        lieu_faits=fpr_data.lieu_faits,
        details=fpr_data.details,
        dangerosite=fpr_data.dangerosite,
        signes_distinctifs=fpr_data.signes_distinctifs,
        conduite=fpr_data.conduite,
        prop_id=fpr_data.prop_id,
        neph=fpr_data.neph,
        num_fijait=fpr_data.num_fijait
    )
    db.add(db_fpr)
    db.commit()
    db.refresh(db_fpr)
    api_log("fpr.create", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fpr", "create"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return db_fpr

@router.put("/update/{fpr_id}/", response_model=fprPublic)
async def update_fpr(fpr_id: int, fpr_update: fprUpdate, db: db_dependency, user: user_dependency, request: Request):
    fpr_record = db.query(fpr).filter(fpr.id == fpr_id).first()
    if not fpr_record:
        raise HTTPException(status_code=404, detail="FPR not found")

    # Capable of partial updates
    update_data = fpr_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(fpr_record, field, value)

    db.commit()
    db.refresh(fpr_record)
    api_log("fpr.update", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fpr", "update"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return fpr_record

@router.delete("/delete/{fpr_id}/")
async def delete_fpr(fpr_id: int, db: db_dependency, user: user_dependency, request: Request):
    fpr_record = db.query(fpr).filter(fpr.id == fpr_id).first()
    if not fpr_record:
        raise HTTPException(status_code=404, detail="FPR not found")
    db.delete(fpr_record)
    db.commit()
    api_log("fpr.delete", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fpr", "delete"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "FPR deleted successfully"}