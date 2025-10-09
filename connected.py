from database import SessionLocal
from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Body, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Annotated, List
from models import Users  # Add this import for the Users model
from passlib.context import CryptContext
import models
from auth import get_current_user
from log import api_log

def connection_required(current_user: Annotated[models.Users, Depends(get_current_user)]):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

router = APIRouter(
    prefix="/connected",
    tags=["connected"],
    dependencies=[Depends(connection_required)]
)

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserPublic(BaseModel):
    id: int
    rp_first_name: str
    rp_last_name: str
    rp_nipol: str
    model_config = ConfigDict(from_attributes=True)

class UserCompleteInscription(BaseModel):
    first_name: str
    last_name: str
    email: str
    rp_birthdate: str
    rp_gender: str
    accepted_cgu: bool
    accepted_privacy: bool
    model_config = ConfigDict(from_attributes=True)

class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    redirect_to: str | None = None  # URL to redirect when clicking on the notification

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]



@router.get("/users/", response_model=List[UserPublic])
async def read_all_users(db: db_dependency, request: Request):
    api_log("users.read_all", level="INFO", request=request, tags=["users", "list"], correlation_id=request.headers.get("x-correlation-id"))
    users = db.query(Users).all()
    return users

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/user/password_change/")
async def change_password(password_change: PasswordChangeRequest, db: db_dependency, user: user_dependency, request: Request):
    # Recharger l'utilisateur dans la session courante (l'objet injecté vient d'une autre session)
    user_db = db.query(Users).filter(Users.id == user.id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    if not bcrypt_context.verify(password_change.old_password, user_db.password):  # type: ignore
        api_log("password.change.failed", level="CRITICAL", request=request, tags=["users", "password"], user_id=user_db.id,email=user_db.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    user_db.token_version += 1 #type: ignore
    user_db.password = bcrypt_context.hash(password_change.new_password)  # type: ignore
    user_db.temp_password = False # type: ignore
    api_log("password.change", level="CRITICAL", request=request, tags=["users", "password"], user_id=user_db.id,email=user_db.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    db.commit()
    db.refresh(user_db)
    return {"message": "Password changed successfully"}

@router.post("/user/discard_all_sessions/")
async def discard_all_sessions(db: db_dependency, user: user_dependency, request: Request):
    user_db = db.query(Users).filter(Users.id == user.id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    user_db.token_version += 1  # type: ignore
    db.commit()
    api_log("session.discard_all", level="CRITICAL", request=request, tags=["users", "session"], user_id=user_db.id,email=user_db.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "All sessions discarded successfully"}

@router.post("/user/inscription_complete/")
async def complete_inscription(user: UserCompleteInscription, db: db_dependency, user_dependency: user_dependency, request: Request):
    user_db = db.query(Users).filter(Users.id == user_dependency.id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    if user_db.inscription_status != "pending": # type: ignore
        raise HTTPException(status_code=400, detail="Inscription already completed or not pending")
    if user_db.first_name != "inconnu" or user_db.last_name != "inconnu": # type: ignore
        raise HTTPException(status_code=400, detail="Inscription already completed")
    
    user_db.first_name = user.first_name # type: ignore
    user_db.last_name = user.last_name #type: ignore
    user_db.email = user.email # type: ignore
    user_db.rp_birthdate = user.rp_birthdate # type: ignore
    user_db.rp_gender = user.rp_gender  # type: ignore
    user_db.accepted_cgu = user.accepted_cgu # type: ignore
    user_db.accepted_privacy = user.accepted_privacy # type: ignore

    notify_user = db.query(Users).filter(Users.privileges.in_(["mod", "admin", "owner"])).all()
    for u in notify_user:
        db_notification = models.Notifications(
            user_id=u.id,
            title=f"{user_db.rp_first_name[0].upper() + user_db.rp_first_name[1:]} {user_db.rp_last_name} a terminé son inscription",
            message=f"L'utilisateur {user_db.rp_first_name} {user_db.rp_last_name} a terminé son inscription et attend une validation.",
            redirect_to=f"/admin/user/{user_db.id}", 
        )
        db.add(db_notification)

    try: 
        db.commit()
        db.refresh(user_db)
        api_log("inscription.complete", level="INFO", request=request, tags=["users", "inscription"], user_id=user_db.id,email=user_db.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
        return {"message": "Inscription completed successfully"}
    except Exception as e:
        db.rollback()
        api_log("inscription.complete.failed", level="ERROR", request=request, tags=["users", "inscription"], user_id=user_db.id,email=user_db.email, error=str(e), correlation_id=request.headers.get("x-correlation-id")) # type: ignore
        raise HTTPException(status_code=500, detail="An error occurred while completing the inscription")