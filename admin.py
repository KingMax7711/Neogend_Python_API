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

def admin_required(current_user: Annotated[models.Users, Depends(get_current_user)], request: Request):
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

dicoAllowToChange = {
    'owner': ['owner', 'admin', 'mod', 'player'],
    'admin': ['mod', 'player'],
    'mod': ['player'],
    'player': []
}

class UserCreate(BaseModel):
    # Enter by admin
    discord_id: str | None = "inconnu"
    rp_first_name: str | None = "inconnu"
    rp_last_name: str | None = "inconnu"
    rp_grade: str | None = "inconnu"
    rp_affectation: str | None = "inconnu"
    rp_qualification: str | None = "afp" 
    rp_nipol: str | None = "inconnu"
    rp_server: str | None = "inconnu"
    rp_service: str | None = "inconnu"  # Police(PN) / Gendarmerie(GN) / Police Municipale(PM)
    rp_qualif: str | None = "afp"

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

class UserAfterCreation(BaseModel):
    id: int
    rp_nipol: int
    temp_password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

protectedUsers = ["admin@admin.com"]

def generate_temp_password():
    import random
    import string
    length = 8
    characters = string.ascii_letters + string.digits
    temp_password = ''.join(random.choice(characters) for i in range(length))
    return temp_password

@router.get("/users/", response_model=List[UserAdminView])
async def read_all_users(db: db_dependency, request: Request, current_user: user_dependency):
    users = db.query(Users).all()
    api_log("users.read_all", level="INFO", request=request, tags=["users", "list"], user_id=current_user.id, email=current_user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return users

@router.get("/users/{user_id}", response_model=UserAdminView)
async def read_specific_user(user_id: int, db: db_dependency, request: Request, current_user: user_dependency):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        api_log("users.read_specific.failed", level="INFO", request=request, tags=["users", "read"], user_id=current_user.id, email=current_user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
        raise HTTPException(status_code=404, detail="User not found")
    api_log("users.read_specific", level="INFO", request=request, tags=["users", "read"], user_id=current_user.id, email=current_user.email, data={"checked_user_id": user.id, "checked_user_nipol": user.rp_nipol}, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return user

@router.post("/set_user_privileges/{user_id}")
async def set_user_privileges(user_id: int, db: db_dependency, request: Request, current_user: user_dependency, privilege: str = Body(..., embed=True)):
    list_of_privileges = ["player", "mod", "admin", "owner"]
    if current_user.privileges != "owner": # type: ignore
        raise HTTPException(status_code=403, detail="Only owner can change user privileges")
    if privilege not in list_of_privileges:
        raise HTTPException(status_code=400, detail=f"Invalid privilege. Must be one of: {', '.join(list_of_privileges)}")
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot change privileges of protected users")
    
    user.privileges = privilege # type: ignore
    db.commit()
    api_log("admin.set_user_privileges", level="INFO", request=request, tags=["admin", "set_privileges"], user_id=current_user.id,email=current_user.email, data={"changed_user_id": user.id, "changed_user_nipol": user.rp_nipol, "new_privilege": privilege}, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "User privileges updated"}


@router.delete("/delete_user/{user_id}")
async def delete_user(user_id: int, db: db_dependency, request: Request, current_user: user_dependency):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot delete protected users")
    if user.privileges not in dicoAllowToChange[current_user.privileges]: # type: ignore
        raise HTTPException(status_code=403, detail="Cannot delete user with equal or higher privileges")
    if user.id == current_user.id: # type: ignore
        raise HTTPException(status_code=403, detail="Cannot delete yourself")
    
    notifications = db.query(models.Notifications).filter(models.Notifications.user_id == user.id).all()
    for notification in notifications:
        db.delete(notification)
    db.commit()
    db.delete(user)
    db.commit()
    api_log("admin.delete_user", level="WARNING", request=request, tags=["admin", "delete_user"], user_id=current_user.id,email=current_user.email, data={"deleted_user_id": user.id, "deleted_user_nipol": user.rp_nipol}, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "User deleted successfully"}

# ---------- Registration ----------
@router.post("/register/", status_code=status.HTTP_201_CREATED, response_model=UserAfterCreation)
async def register_user(user: UserCreate, db: db_dependency, request: Request, current_user: user_dependency):
    # Hash the password
    temp_password = generate_temp_password()
    hashed_password = bcrypt_context.hash(temp_password)  # Default password, should be changed by user later
    db_user = Users(
        # Entered by user later
        first_name="inconnu",
        last_name="inconnu",
        email="inconnu",
        rp_gender="male",
        rp_birthdate=date.today(),

        # Entered by admin
        rp_first_name=user.rp_first_name,
        rp_last_name=user.rp_last_name,
        discord_id=user.discord_id,
        rp_grade=user.rp_grade,
        rp_affectation=user.rp_affectation,
        rp_qualif=user.rp_qualification, #! ATTENTION rp_qualification n'existe pas dans la base de donnée, c'est rp_qualif
        rp_nipol=user.rp_nipol,
        rp_server=user.rp_server,
        rp_service=user.rp_service,

        # Force or Generated
        password=hashed_password,
        inscription_status="pending",
        inscription_date=date.today(),
        privileges="player",
        temp_password=True,  

    )


    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        new_user = db.query(Users).filter(Users.rp_nipol == db_user.rp_nipol).first()
        if not new_user:
            raise HTTPException(status_code=500, detail="User creation failed")
        db_notifications = models.Notifications(
            user_id=new_user.id,  # type: ignore
            title="Complétez votre inscription",
            message="Rendez-vous dans votre profil pour compléter votre inscription et choisir votre mot de passe. \n Ensuite, un administrateur validera votre inscription.",
            redirect_to="/profile",
        )
        db.add(db_notifications)
        db.commit()
        api_log("admin.register_user", level="INFO", request=request, tags=["admin", "register_user"], user_id=current_user.id,email=current_user.email,data={"created_user_id": db_user.id, "created_user_nipol": db_user.rp_nipol} ,correlation_id=request.headers.get("x-correlation-id")) # type: ignore
        return {"id": db_user.id, "rp_nipol": db_user.rp_nipol, "temp_password": temp_password}
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
    model_config = ConfigDict(from_attributes=True)

@router.patch("/users_update/{user_id}", response_model=UserAdminView)
async def update_user(user_id: int, user_update: UserUpdate, db: db_dependency, request: Request, current_user: user_dependency):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot update protected users")
    if user.privileges not in dicoAllowToChange[current_user.privileges]: # type: ignore
        raise HTTPException(status_code=403, detail="Cannot update user with equal or higher privileges")

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
    api_log("admin.update_user", level="INFO", request=request, tags=["admin", "update_user"], user_id=current_user.id,email=current_user.email, data={"updated_user_id": user.id, "updated_user_nipol": user.rp_nipol}, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return user


@router.post("/users/{user_id}/password", response_model=UserAfterCreation)
async def update_password(user_id: int, db: db_dependency, request: Request, current_user: user_dependency):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot update protected users")
    if user.privileges not in dicoAllowToChange[current_user.privileges]: # type: ignore
        raise HTTPException(status_code=403, detail="Cannot update user with equal or higher privileges")
    temp_password = generate_temp_password()
    user.password = bcrypt_context.hash(temp_password)  # type: ignore
    user.temp_password = True # type: ignore
    db.commit()
    api_log("admin.update_password", level="CRITICAL", request=request, tags=["admin", "update_password"], user_id=current_user.id,email=current_user.email,data={"updated_user_id": user.id, "updated_user_nipol": user.rp_nipol} ,correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"id": user.id, "rp_nipol": user.rp_nipol, "temp_password": temp_password} # type: ignore

@router.post("/users/disconnect_all")
async def disconnect_all_users(db: db_dependency, request: Request, current_user: user_dependency):
    if current_user.privileges != "owner": # type: ignore
        raise HTTPException(status_code=403, detail="Only owner can disconnect all users")
    users = db.query(Users).all()
    for user in users:
        user.token_version += 1  # type: ignore # Incrémente la version du token pour forcer la déconnexion
    db.commit()
    api_log("admin.disconnect_all_users", level="CRITICAL", request=request, tags=["admin", "disconnect_all"], user_id=current_user.id,email=current_user.email, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "All users disconnected"}

@router.post("/users/disconnect/{user_id}")
async def disconnect_user(user_id: int, db: db_dependency, request: Request, current_user: user_dependency):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email in protectedUsers:
        raise HTTPException(status_code=403, detail="Cannot disconnect protected users")
    if user.privileges not in dicoAllowToChange[current_user.privileges]: # type: ignore
        raise HTTPException(status_code=403, detail="Cannot disconnect user with equal or higher privileges")
    user.token_version += 1  # type: ignore # Incrémente la version du token pour forcer la déconnexion
    db.commit()
    api_log("admin.disconnect_user", level="CRITICAL", request=request, tags=["admin", "disconnect_user"], user_id=current_user.id,email=current_user.email, data={"disconnected_user_id": user.id, "disconnected_user_nipol": user.rp_nipol}, correlation_id=request.headers.get("x-correlation-id")) # type: ignore
    return {"message": "User disconnected"}