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
    prefix="/infractions",
    tags=["infractions"],
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

class infractionCreate(BaseModel):
    article: str | None = None
    classe: str
    natinf: str | None = None
    points: int
    nipol: str
    date_infraction: str
    details: str  | None = None
    statut: str
    neph: int
    model_config = ConfigDict(from_attributes=True)

class infractionUpdate(BaseModel):
    article: str | None = None
    classe: str | None = None
    natinf: str | None = None
    points: int | None = None
    nipol: str | None = None
    date_infraction: str | None = None
    details: str | None = None
    statut: str | None = None
    neph: int | None = None
    model_config = ConfigDict(from_attributes=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

@router.get("/read/", response_model=List[infractionPublic])
async def read_all_infractions(db: db_dependency, user: user_dependency, request: Request):
    infractions = db.query(models.infractions_routieres).all()
    api_log("infractions.read_all", level="INFO", request=request,email=user.email, user_id=user.id, tags=["infractions", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return infractions

@router.get("/read/{infraction_id}/", response_model=infractionPublic)
async def read_infraction(infraction_id: int, db: db_dependency, user: user_dependency, request: Request):
    infraction = db.query(models.infractions_routieres).filter(models.infractions_routieres.id == infraction_id).first()
    if not infraction:
        raise HTTPException(status_code=404, detail="Infraction not found")
    api_log("infractions.read_one", level="INFO", request=request,email=user.email, user_id=user.id, tags=["infractions", "detail"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return infraction

@router.get("/read/by_neph/{neph}/", response_model=List[infractionPublic])
async def read_infractions_by_neph(neph: int, db: db_dependency, user: user_dependency, request: Request):
    infractions = db.query(models.infractions_routieres).filter(models.infractions_routieres.neph == neph).all()
    api_log("infractions.read_by_neph", level="INFO", request=request,email=user.email, user_id=user.id, tags=["infractions", "list"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return infractions

@router.post("/create/", response_model=infractionPublic)
async def create_infraction(infraction: infractionCreate, db: db_dependency, user: user_dependency, request: Request):
    db_infraction = models.infractions_routieres(
        article=infraction.article,
        classe=infraction.classe,
        natinf=infraction.natinf,
        points=infraction.points,
        nipol=infraction.nipol,
        date_infraction=infraction.date_infraction,
        details=infraction.details,
        statut=infraction.statut,
        neph=infraction.neph
    )
    try:
        db.query(models.fnpc).filter(models.fnpc.neph == infraction.neph).one()
    except Exception:
        raise HTTPException(status_code=404, detail="NEPH not matched with any FNPC")
    
    matchFnpc = db.query(models.fnpc).filter(models.fnpc.neph == infraction.neph).one()
    matchFnpc.points -= infraction.points #type: ignore
    if matchFnpc.points < 0: #type: ignore
        matchFnpc.points = 0 #type: ignore
    db.commit()
    db.add(db_infraction)
    db.commit()
    db.refresh(db_infraction)
    api_log("infractions.create", level="INFO", request=request,email=user.email, user_id=user.id, tags=["infractions", "create"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return db_infraction

@router.put("/update/{infraction_id}/", response_model=infractionPublic)
async def update_infraction(infraction_id: int, infraction_update: infractionUpdate, db: db_dependency, user: user_dependency, request: Request):
    infraction = db.query(models.infractions_routieres).filter(models.infractions_routieres.id == infraction_id).first()
    if not infraction:
        raise HTTPException(status_code=404, detail="Infraction not found")

    # Capable of partial updates
    update_data = infraction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(infraction, field, value)

    try:
        db.query(models.fnpc).filter(models.fnpc.neph == infraction.neph).one()
    except Exception:
        raise HTTPException(status_code=404, detail="NEPH not matched with any FNPC")
    db.commit()
    db.refresh(infraction)
    api_log("infractions.update", level="INFO", request=request,email=user.email, user_id=user.id, tags=["infractions", "update"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return infraction

@router.delete("/delete/{infraction_id}/")
async def delete_infraction(infraction_id: int, db: db_dependency, user: user_dependency, request: Request):
    infraction = db.query(models.infractions_routieres).filter(models.infractions_routieres.id == infraction_id).first()
    if not infraction:
        raise HTTPException(status_code=404, detail="Infraction not found")
    db.delete(infraction)
    db.commit()
    api_log("infractions.delete", level="INFO", request=request,email=user.email, user_id=user.id, tags=["infractions", "delete"], correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "Infraction deleted successfully"}