from sqlalchemy.orm import Session
from .models import User
from ...domain.ports.user_repository_port import UserRepositoryPort

class UserRepository(UserRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username:str):
        return self.db.query(User).filter(User.username == username).first()
    
    def create_user(self, username: str, hashed_password: str):
        new_user = User(username=username, hashed_password=hashed_password)
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user