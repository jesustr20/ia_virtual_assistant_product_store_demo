from ..domain.ports.user_repository_port import UserRepositoryPort
from ..infrastructure.security.jwt_handler import hash_password, verify_password, create_access_token
from ..core.exceptions import InvalidCredentialsError, UserAlreadyExistsError

class AuthService:
    def __init__(self, repo: UserRepositoryPort):
        self.repo = repo

    def register(self, username: str, password: str):
        existing = self.repo.get_by_username(username)
        if existing:
            raise UserAlreadyExistsError()
        hashed = hash_password(password)
        return self.repo.create_user(username, hashed)

    def login(self, username: str, password: str) -> str:
        user = self.repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        token = create_access_token({"sub": user.username})
        return token