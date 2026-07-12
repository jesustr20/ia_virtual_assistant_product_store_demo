from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...infrastructure.db.session import get_db
from ...infrastructure.db.user_repository import UserRepository
from ...application.auth_service import AuthService
from ..schemas.user_schemas import UserCreate

router = APIRouter()

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo)

@router.post("/register")
def register(user: UserCreate, auth_sercice: AuthService=Depends(get_auth_service)):
    try:
        new_user = auth_sercice.register(user.username, user.password)
        return {"id": new_user.id, "username":new_user.username}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login")
def login(username: str, password: str, auth_service: AuthService=Depends(get_auth_service)):
    try:
        token = auth_service.login(username, password)
        return {"access_token":token, "token_type":"bearer"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))