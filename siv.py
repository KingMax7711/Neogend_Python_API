from datetime import date
from database import SessionLocal
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Annotated, List
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
	prefix="/siv",
	tags=["siv"],
	dependencies=[Depends(connection_required)],
)


class sivPublic(BaseModel):
	id: int

	# Propriétaire
	prop_id: int
	co_prop_id: int | None = None

	# Certificat d'immatriculation
	ci_etat_administratif: str | None = None
	ci_numero_immatriculation: str | None = None
	ci_date_premiere_circulation: date | None = None
	ci_date_certificat: date | None = None

	# Véhicule
	vl_etat_administratif: str | None = None
	vl_marque: str | None = None
	vl_denomination_commerciale: str | None = None
	vl_version: str | None = None
	vl_couleur_dominante: str | None = None

	# Caractéristiques techniques
	tech_puissance_kw: int | None = None
	tech_puissance_ch: int | None = None
	tech_puissance_fiscale: int | None = None
	tech_cylindree: int | None = None
	tech_carburant: str | None = None
	tech_emissions_co2: int | None = None
	tech_poids_vide: int | None = None
	tech_poids_ptac: int | None = None
	tech_places_assises: int | None = None
	tech_places_debout: int | None = None

	# Contrôles techniques
	ct_date_echeance: date | None = None

	# Assurance
	as_assureur: str | None = None
	as_date_contrat: date | None = None

	model_config = ConfigDict(from_attributes=True)


class sivCreate(BaseModel):
	# Propriétaire
	prop_id: int
	co_prop_id: int | None = None

	# Certificat d'immatriculation
	ci_etat_administratif: str | None = None
	ci_numero_immatriculation: str | None = None
	ci_date_premiere_circulation: date | None = None
	ci_date_certificat: date | None = None

	# Véhicule
	vl_etat_administratif: str | None = None
	vl_marque: str | None = None
	vl_denomination_commerciale: str | None = None
	vl_version: str | None = None
	vl_couleur_dominante: str | None = None

	# Caractéristiques techniques
	tech_puissance_kw: int | None = None
	tech_puissance_ch: int | None = None
	tech_puissance_fiscale: int | None = None
	tech_cylindree: int | None = None
	tech_carburant: str | None = None
	tech_emissions_co2: int | None = None
	tech_poids_vide: int | None = None
	tech_poids_ptac: int | None = None
	tech_places_assises: int | None = None
	tech_places_debout: int | None = None

	# Contrôles techniques
	ct_date_echeance: date | None = None

	# Assurance
	as_assureur: str | None = None
	as_date_contrat: date | None = None

	model_config = ConfigDict(from_attributes=True)


class sivUpdate(BaseModel):
	# All optional for partial updates
	prop_id: int | None = None
	co_prop_id: int | None = None

	ci_etat_administratif: str | None = None
	ci_numero_immatriculation: str | None = None
	ci_date_premiere_circulation: date | None = None
	ci_date_certificat: date | None = None

	vl_etat_administratif: str | None = None
	vl_marque: str | None = None
	vl_denomination_commerciale: str | None = None
	vl_version: str | None = None
	vl_couleur_dominante: str | None = None

	tech_puissance_kw: int | None = None
	tech_puissance_ch: int | None = None
	tech_puissance_fiscale: int | None = None
	tech_cylindree: int | None = None
	tech_carburant: str | None = None
	tech_emissions_co2: int | None = None
	tech_poids_vide: int | None = None
	tech_poids_ptac: int | None = None
	tech_places_assises: int | None = None
	tech_places_debout: int | None = None

	ct_date_echeance: date | None = None

	as_assureur: str | None = None
	as_date_contrat: date | None = None

	model_config = ConfigDict(from_attributes=True)


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]


@router.get("/read/", response_model=List[sivPublic])
async def read_all_siv(db: db_dependency, user: user_dependency, request: Request):
	records = db.query(models.siv).all()
	api_log("siv.read_all", level="INFO", request=request, email=user.email, user_id=user.id, tags=["siv", "list"], correlation_id=request.headers.get("x-correlation-id"))  # type: ignore
	return records


@router.get("/read/{siv_id}/", response_model=sivPublic)
async def read_siv(siv_id: int, db: db_dependency, user: user_dependency, request: Request):
	record = db.query(models.siv).filter(models.siv.id == siv_id).first()
	if not record:
		raise HTTPException(status_code=404, detail="siv record not found")
	api_log("siv.read_one", level="INFO", request=request, email=user.email, user_id=user.id, tags=["siv", "detail"], correlation_id=request.headers.get("x-correlation-id"))  # type: ignore
	return record


@router.post("/create/", response_model=sivPublic)
async def create_siv(payload: sivCreate, db: db_dependency, user: user_dependency, request: Request):
	new_record = models.siv(**payload.model_dump(exclude_unset=True))
	db.add(new_record)
	db.commit()
	db.refresh(new_record)
	api_log("siv.create", level="INFO", request=request, email=user.email, user_id=user.id, tags=["siv", "create"], correlation_id=request.headers.get("x-correlation-id"))  # type: ignore
	return new_record


@router.put("/update/{siv_id}/", response_model=sivPublic)
async def update_siv(siv_id: int, payload: sivUpdate, db: db_dependency, user: user_dependency, request: Request):
	record = db.query(models.siv).filter(models.siv.id == siv_id).first()
	if not record:
		raise HTTPException(status_code=404, detail="siv record not found")

	update_data = payload.model_dump(exclude_unset=True)
	for field, value in update_data.items():
		setattr(record, field, value)

	db.commit()
	db.refresh(record)
	api_log("siv.update", level="INFO", request=request, email=user.email, user_id=user.id, tags=["siv", "update"], correlation_id=request.headers.get("x-correlation-id"))  # type: ignore
	return record


@router.delete("/delete/{siv_id}/")
async def delete_siv(siv_id: int, db: db_dependency, user: user_dependency, request: Request):
	record = db.query(models.siv).filter(models.siv.id == siv_id).first()
	if not record:
		raise HTTPException(status_code=404, detail="siv record not found")
	db.delete(record)
	db.commit()
	api_log("siv.delete", level="WARNING", request=request, email=user.email, user_id=user.id, tags=["siv", "delete"], correlation_id=request.headers.get("x-correlation-id"))  # type: ignore
	return {"message": f"siv {siv_id} deleted successfully"}

