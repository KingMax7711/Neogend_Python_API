from datetime import date, datetime
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
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(connection_required)]
)

class NotificationPublic(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    redirect_to: str | None = None  # URL to redirect when clicking on the notification
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    redirect_to: str | None = None  # URL to redirect when clicking on the notification

class NotificationCreateAll(BaseModel):
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

@router.post("/create/", response_model=NotificationPublic)
async def create_notification(notification: NotificationCreate, db: db_dependency, request: Request, user: user_dependency):
    db_notification = models.Notifications(
        user_id=notification.user_id,
        title=notification.title,
        message=notification.message,
        redirect_to=notification.redirect_to,
    is_read=False
    )
    if not db.query(models.Users).filter(models.Users.id == notification.user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    api_log("notifications.create", level="INFO", request=request, tags=["notifications", "create"], user_id=user.id,email=user.email, data={"notification_id": db_notification.id, "notify_user": notification.user_id},correlation_id=request.headers.get("x-correlation-id")) #type: ignore
    return db_notification

@router.post("/create_all/", response_model=NotificationPublic)
async def create_notification_all(notification: NotificationCreateAll, db: db_dependency, request: Request, user: user_dependency):
    users = db.query(models.Users).all()
    last_notification = None
    for u in users:
        db_notification = models.Notifications(
            user_id=u.id,
            title=notification.title,
            message=notification.message,
            redirect_to=notification.redirect_to,
            is_read=False
        )
        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)
        last_notification = db_notification
    if last_notification is None:
        raise HTTPException(status_code=400, detail="No users found to send notifications")
    api_log("notifications.create_all", level="INFO", request=request, tags=["notifications", "create_all"], user_id=user.id,email=user.email, correlation_id=request.headers.get("x-correlation-id")) #type: ignore
    return last_notification