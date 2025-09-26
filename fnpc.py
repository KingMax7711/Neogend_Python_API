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
    can_use = ["admin", "owner"]
    if not current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if current_user.privileges not in can_use:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

router = APIRouter(
    prefix="/fnpc",
    tags=["fnpc"],
    dependencies=[Depends(connection_required)]
)

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

class fnpcCreate(BaseModel):
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

class fnpcUpdate(BaseModel):
    neph: int | None = None
    numero_titre: int | None = None
    date_delivrance: date | None = None
    prefecture_delivrance: str | None = None
    date_expiration: date | None = None
    statut: str | None = None
    validite: str | None = None

    cat_am: bool | None = None
    cat_am_delivrance: date | None = None
    cat_a1: bool | None = None
    cat_a1_delivrance: date | None = None
    cat_a2: bool | None = None
    cat_a2_delivrance: date | None = None
    cat_a: bool | None = None
    cat_a_delivrance: date | None = None
    cat_b1: bool | None = None
    cat_b1_delivrance: date | None = None
    cat_b: bool | None = None
    cat_b_delivrance: date | None = None
    cat_c1: bool | None = None
    cat_c1_delivrance: date | None = None
    cat_c: bool | None = None
    cat_c_delivrance: date | None = None
    cat_d1: bool | None = None
    cat_d1_delivrance: date | None = None
    cat_d: bool | None = None
    cat_d_delivrance: date | None = None
    cat_be: bool | None = None
    cat_be_delivrance: date | None = None
    cat_c1e: bool | None = None
    cat_c1e_delivrance: date | None = None
    cat_ce: bool | None = None
    cat_ce_delivrance: date | None = None
    cat_d1e: bool | None = None
    cat_d1e_delivrance: date | None = None
    cat_de: bool | None = None
    cat_de_delivrance: date | None = None

    code_restriction: str | None = None
    probatoire: bool | None = None
    date_probatoire: date | None = None
    points: int | None = None

    prop_id: int | None = None

    model_config = ConfigDict(from_attributes=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

@router.get("/read/", response_model=List[fnpcPublic])
async def read_all_fnpcs(db: db_dependency, user: user_dependency, request: Request):
    fnpcs = db.query(models.fnpc).all()
    api_log("fnpc.read_all", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fnpc", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return fnpcs

@router.get("/read/{fnpc_id}/", response_model=fnpcPublic)
async def read_fnpc(fnpc_id: int, db: db_dependency, user: user_dependency, request: Request):
    fnpc = db.query(models.fnpc).filter(models.fnpc.id == fnpc_id).first()
    if not fnpc:
        raise HTTPException(status_code=404, detail="fnpc not found")
    api_log("fnpc.read", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fnpc", "read"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return fnpc

@router.post("/create/", response_model=fnpcPublic)
async def create_fnpc(fnpc: fnpcCreate, db: db_dependency, user: user_dependency, request: Request):
    new_fnpc = models.fnpc(**fnpc.model_dump())
    db.add(new_fnpc)
    db.commit()
    db.refresh(new_fnpc)
    api_log("fnpc.create", level="INFO", request=request,email=user.email, user_id=user.id, tags=["fnpc", "create"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return new_fnpc

@router.put("/update/{fnpc_id}/", response_model=fnpcPublic)
async def update_fnpc(fnpc_id: int, fnpc_update: fnpcUpdate, db: db_dependency, user: user_dependency, request: Request):
    # Fetch existing record
    record = db.query(models.fnpc).filter(models.fnpc.id == fnpc_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="fnpc not found")

    # Partial update: only update provided fields
    update_data = fnpc_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    api_log("fnpc.update", level="INFO", request=request, email=user.email, user_id=user.id, tags=["fnpc", "update"], correlation_id=request.headers.get("x-correlation-id"))  # type: ignore
    return record

@router.delete("/delete/{fnpc_id}/")
async def delete_fnpc(fnpc_id: int, db: db_dependency, user: user_dependency, request: Request):
    fnpc = db.query(models.fnpc).filter(models.fnpc.id == fnpc_id).first()
    if not fnpc:
        raise HTTPException(status_code=404, detail="fnpc not found")
    db.delete(fnpc)
    db.commit()
    api_log("fnpc.delete", level="WARNING", request=request,email=user.email, user_id=user.id, tags=["fnpc", "delete"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"detail": f"fnpc {fnpc_id} deleted"}