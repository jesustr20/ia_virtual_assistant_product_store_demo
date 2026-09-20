"""Configuración compartida de pytest.

Se carga antes de que los tests importen módulos de `app`. Setea las env vars que
esos módulos leen a nivel de import (como `jwt_handler.SECRET_KEY`) para que los
tests unitarios no dependan de un `.env` real ni de secretos del entorno.
"""

import os

# jwt_handler hace `SECRET_KEY = os.environ.get("SECRET_KEY")` al importarse; sin esto
# `create_access_token`/`decode_access_token` fallarían (jwt necesita una clave).
# Usamos >= 32 bytes para evitar el warning de clave HMAC corta de pyjwt.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-0123456789abcdef")
