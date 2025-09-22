from token import RPAR
from database import SessionLocal
from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Body, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Annotated, List
from models import Users  # Add this import for the Users model
from passlib.context import CryptContext
import models
from auth import get_current_user
from datetime import date
from log import api_log

def admin_required(current_user: Annotated[models.Users, Depends(get_current_user)]):
    approvedList = ["admin", "owner"]
    if not getattr(current_user, "privileges", "player") in approvedList:
        api_log("admin.access_denied", level="INFO", request=request, tags=["auth", "admin"], user_id=current_user.id,email=current_user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
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
    temp_password: bool
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
async def read_all_users(db: db_dependency, request: Request):
    users = db.query(Users).all()
    api_log("users.read_all", level="INFO", request=request, tags=["users", "list"], correlation_id=request.headers.get("x-correlation-id"))
    return users

@router.get("/users/{user_id}", response_model=UserAdminView)
async def read_specific_user(user_id: int, db: db_dependency, request: Request):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        api_log("users.read_specific.failed", level="INFO", request=request, tags=["users", "read"], user_id=user.id,email=user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/set_user_privileges/{user_id}")
async def set_user_privileges(user_id: int, db: db_dependency, request: Request, privilege: str = Body(..., embed=True)):
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
    api_log("admin.set_user_privileges", level="INFO", request=request, tags=["admin", "set_privileges"], user_id=user.id,email=user.email, new_privilege=privilege, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "User privileges updated"}


@router.delete("/delete_user/{user_id}")
async def delete_user(user_id: int, db: db_dependency, request: Request):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot delete protected users")
    db.delete(user)
    db.commit()
    api_log("admin.delete_user", level="WARNING", request=request, tags=["admin", "delete_user"], user_id=user.id,email=user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "User deleted successfully"}

# ---------- Registration ----------
@router.post("/register/", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: db_dependency, request: Request):
    # Hash the password
    hashed_password = bcrypt_context.hash("temporaire")  # Default password, should be changed by user later
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
        rp_qualif="afp", #TODO: DEFAUT A CHANGER (Voir IRL)
        rp_nipol=user.rp_nipol,
        rp_server=user.rp_server,
        rp_service=user.rp_service,
        privileges='player',
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        api_log("admin.register_user", level="INFO", request=request, tags=["admin", "register_user"], user_id=db_user.id,email=db_user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
        return {"message": "User registered successfully"}
    except Exception as e:
        db.rollback()
        if db.query(Users).filter(Users.rp_nipol == user.rp_nipol).first():
            raise HTTPException(status_code=409, detail="NIPOL already registered")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
# ---------- Change on User by Admin ----------
class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    discord_id: str | None = None
    inscription_date: date | None = None
    inscription_status: str | None = None  # valid / pending / denied
    rp_first_name: str | None = None
    rp_last_name: str | None = None
    rp_birthdate: date | None = None
    rp_gender: str | None = None
    rp_grade: str | None = None
    rp_affectation: str | None = None
    rp_qualif: str | None = None
    rp_nipol: str | None = None
    rp_server: str | None = None
    rp_service: str | None = None  # Police(PN) / Gendarmerie(GN) / Police Municipale(PM)
    privileges: str | None = None
    model_config = ConfigDict(from_attributes=True)

@router.patch("/users_update/{user_id}", response_model=UserAdminView)
async def update_user(user_id: int, user_update: UserUpdate, db: db_dependency, request: Request):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot update protected users")

    update_data = user_update.model_dump(exclude_unset=True)

    # NIPOL uniqueness check if NIPOL change requested
    new_nipol = update_data.get("rp_nipol")
    if new_nipol and new_nipol != user.rp_nipol:
        if db.query(Users).filter(Users.rp_nipol == new_nipol).first():
            raise HTTPException(status_code=409, detail="NIPOL already in use")

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    api_log("admin.update_user", level="INFO", request=request, tags=["admin", "update_user"], user_id=user.id,email=user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return user

class PasswordUpdate(BaseModel):
    new_password: str

@router.post("/users/{user_id}/password")
async def update_password(user_id: int, body: PasswordUpdate, db: db_dependency, request: Request):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot update protected users")
    user.password = bcrypt_context.hash(body.new_password)  # type: ignore
    user.temp_password = True # type: ignore
    db.commit()
    api_log("admin.update_password", level="INFO", request=request, tags=["admin", "update_password"], user_id=user.id,email=user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "Password updated"}
