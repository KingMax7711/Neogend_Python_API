from database import SessionLocal
from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Annotated, List
from models import Users  # Add this import for the Users model
import models
from auth import get_current_user

def connection_required(current_user: Annotated[models.Users, Depends(get_current_user)]):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

router = APIRouter(
    prefix="/connected",
    tags=["connected"],
    dependencies=[Depends(connection_required)]
)


class UserPublic(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    is_admin: bool
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
async def read_all_users(db: db_dependency):
    users = db.query(Users).all()
    return users