from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...infrastructure.db.session import get_db
from ...infrastructure.db.user_repository import UserRepository
from ...application.auth_service import AuthService
from ..schemas.user_schemas import UserCreate, UserLogin

router = APIRouter()

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo)

@router.post("/register")
def register(user: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    new_user = auth_service.register(user.username, user.password)
    return {"id": new_user.id, "username": new_user.username}

@router.post("/login")
def login(credentials: UserLogin, auth_service: AuthService = Depends(get_auth_service)):
    token = auth_service.login(credentials.username, credentials.password)
    return {"access_token": token, "token_type": "bearer"}