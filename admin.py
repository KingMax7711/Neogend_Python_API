from token import RPAR
from database import SessionLocal
from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Annotated, List
from models import Users  # Add this import for the Users model
from passlib.context import CryptContext
import models
from auth import get_current_user
from datetime import date

def admin_required(current_user: Annotated[models.Users, Depends(get_current_user)]):
    approvedList = ["admin", "owner"]
    if not getattr(current_user, "privileges", "player") in approvedList:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(admin_required)]
)

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    discord_id: str | None = "inconnu"
    rp_first_name: str | None = "inconnu"
    rp_last_name: str | None = "inconnu"
    rp_birthdate: date | None = date.today()
    rp_gender: str | None = "inconnu"
    rp_grade: str | None = "inconnu"
    rp_affectation: str | None = "inconnu"
    rp_nipol: str | None = "inconnu"
    rp_server: str | None = "inconnu"
    rp_service: str | None = "inconnu"  # Police(PN) / Gendarmerie(GN) / Police Municipale(PM)
    model_config = ConfigDict(from_attributes=True)

class UserAdminView(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    discord_id: str | None
    inscription_date: date | None
    inscription_status: str | None  # valid / pending / denied
    rp_first_name: str | None
    rp_last_name: str | None
    rp_birthdate: date | None  # Utilisez date si vous voulez une conversion automatique
    rp_gender: str | None
    rp_grade: str | None
    rp_affectation: str | None
    rp_qualif: str | None
    rp_nipol: str | None
    rp_server: str | None
    rp_service: str | None  # Police(PN) / Gendarmerie(GN) / Police Municipale(PM)
    privileges: str 

    model_config = ConfigDict(from_attributes=True)

class SetUserAdminRequest(BaseModel):
    is_admin: bool


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

protectedUsers = ["maxime.czegledi@gmail.com"]

@router.get("/users/", response_model=List[UserAdminView])
async def read_all_users(db: db_dependency):
    users = db.query(Users).all()
    return users

@router.get("/users/{user_id}", response_model=UserAdminView)
async def read_specific_user(user_id: int, db: db_dependency):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/set_user_privileges/{user_id}")
async def set_user_privileges(user_id: int, db: db_dependency, privilege: str = Body(..., embed=True)):
    list_of_privileges = ["player", "mod", "admin", "owner"]
    if privilege not in list_of_privileges:
        raise HTTPException(status_code=400, detail=f"Invalid privilege. Must be one of: {', '.join(list_of_privileges)}")
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot change privileges of protected users")
    user.privileges = privilege # type: ignore
    db.commit()
    return {"message": "User privileges updated"}


@router.delete("/delete_user/{user_id}")
async def delete_user(user_id: int, db: db_dependency):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot delete protected users")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

# ---------- Registration ----------
@router.post("/register/", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: db_dependency):
    # Hash the password
    hashed_password = bcrypt_context.hash("password")  # Default password, should be changed by user later
    db_user = Users(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password=hashed_password,
        discord_id=user.discord_id,
        inscription_status="pending",
        inscription_date=date.today(),
        rp_gender=user.rp_gender,
        rp_first_name=user.rp_first_name,
        rp_last_name=user.rp_last_name,
        rp_birthdate=user.rp_birthdate,
        rp_grade=user.rp_grade,
        rp_affectation=user.rp_affectation,
        rp_qualif="",
        rp_nipol=user.rp_nipol,
        rp_server=user.rp_server,
        rp_service=user.rp_service,
        privileges='player',
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return {"message": "User registered successfully"}
    except Exception as e:
        db.rollback()
        if db.query(Users).filter(Users.email == user.email).first():
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(status_code=500, detail="Internal Server Error")