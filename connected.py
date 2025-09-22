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
    first_name: str
    last_name: str
    email: str
    model_config = ConfigDict(from_attributes=True)



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
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    user_db.token_version += 1 #type: ignore
    user_db.password = bcrypt_context.hash(password_change.new_password)  # type: ignore
    user_db.temp_password = False # type: ignore
    api_log("password.change", level="WARNING", request=request, tags=["users", "password"], user_id=user_db.id,email=user_db.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    db.commit()
    db.refresh(user_db)
    return {"message": "Password changed successfully"}