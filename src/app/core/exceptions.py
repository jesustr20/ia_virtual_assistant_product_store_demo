class AppException(Exception):
    """Excepción base para errores de negocio de la app."""
    def __init__(self, message: str, code: str = "internal_error", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(message, code="not_found", status_code=404)


class InvalidCredentialsError(AppException):
    def __init__(self, message: str = "Credenciales inválidas"):
        super().__init__(message, code="invalid_credentials", status_code=401)


class UserAlreadyExistsError(AppException):
    def __init__(self, message: str = "El usuario ya existe"):
        super().__init__(message, code="user_already_exists", status_code=400)