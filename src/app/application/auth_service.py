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
        # El primer usuario del sistema es admin automáticamente; el resto, user (issue #28).
        role = "admin" if self.repo.count_users() == 0 else "user"
        return self.repo.create_user(username, hashed, role)

    def login(self, username: str, password: str) -> str:
        user = self.repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        token = create_access_token({"sub": user.username, "role": user.role})
        return token