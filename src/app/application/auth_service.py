from ..domain.ports.user_repository_port import UserRepositoryPort
from ..infrastructure.security.jwt_handler import hash_password, verify_password, create_access_token

class AuthService:
    def __init__(self, repo: UserRepositoryPort):
        self.repo = repo

    def register(self, username: str, password: str):
        existing = self.repo.get_by_username(username)
        if existing:
            raise ValueError("Username already exists")
        hashed = hash_password(password)
        return self.repo.create_user(username, hashed)
    
    def login(self, username: str, password: str) -> str:
        user = self.repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Credenciales inválidas")
        token = create_access_token({"sub": user.username})
        return token