from datetime import date, datetime
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
    if not current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

router = APIRouter(
    prefix="/notifications_public",
    tags=["notifications_public"],
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

@router.get("/notifications/get_all/", response_model=List[NotificationPublic])
async def get_all_notifications(db: db_dependency, user: user_dependency):
    notifications = db.query(models.Notifications).filter(models.Notifications.user_id == user.id).all()
    return notifications

@router.get("/notifications/get_unread/", response_model=List[NotificationPublic])
async def get_unread_notifications(db: db_dependency, user: user_dependency):
    notifications = db.query(models.Notifications).filter(
        models.Notifications.user_id == user.id,
        models.Notifications.is_read == False
    ).all()
    return notifications

@router.put("/notifications/mark_as_read/{notification_id}/", response_model=NotificationPublic)
async def mark_notification_as_read(notification_id: int, db: db_dependency, user: user_dependency, request: Request):
    notification = db.query(models.Notifications).filter(models.Notifications.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != user.id: #type: ignore
        raise HTTPException(status_code=403, detail="Not authorized to mark this notification as read")
    notification.is_read = True # type: ignore
    db.commit()
    db.refresh(notification)
    api_log("notification.mark_as_read", level="INFO", user_id=notification.user_id, email=user.email, data={"notification_id": notification.id}, tags=["notifications", "read"], correlation_id=request.headers.get("X-Correlation-ID"), request=request) # type: ignore
    return notification

@router.put("/notifications/mark_all_as_read/", response_model=List[NotificationPublic])
async def mark_all_notifications_as_read(db: db_dependency, user: user_dependency, request: Request):
    notifications = db.query(models.Notifications).filter(
        models.Notifications.user_id == user.id,
        models.Notifications.is_read == False
    ).all()
    for notification in notifications:
        notification.is_read = True # type: ignore
    db.commit()
    api_log("notifications.mark_all_as_read", level="INFO", user_id=user.id, email=user.email, data={"marked_count": len(notifications)}, tags=["notifications", "read_all"], correlation_id=request.headers.get("X-Correlation-ID"), request=request) # type: ignore
    return notifications