from abc import ABC, abstractmethod
from typing import Optional

class UserRepositoryPort(ABC):

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[object]:
        """"Busca un usuario por username. Devuelve None sino existe."""
        pass

    @abstractmethod
    def create_user(self, username: str, hashed_password: str, role: str) -> object:
        """"Crea un usuario nuevo con la contraseña ya hasheada y un rol dado."""
        pass

    @abstractmethod
    def count_users(self) -> int:
        """Devuelve la cantidad total de usuarios registrados.

        Se usa para decidir el rol del primer usuario (admin) en el registro (issue #28).
        """
        pass