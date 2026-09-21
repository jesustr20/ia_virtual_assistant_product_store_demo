import pytest

from app.api.dependencies import require_admin
from app.core.exceptions import ForbiddenError
from app.infrastructure.security.jwt_handler import create_access_token


def test_require_admin_allows_admin_token():
    token = create_access_token({"sub": "alice", "role": "admin"})

    username = require_admin(token=token, username="alice")

    assert username == "alice"


def test_require_admin_rejects_user_token():
    token = create_access_token({"sub": "bob", "role": "user"})

    with pytest.raises(ForbiddenError) as exc_info:
        require_admin(token=token, username="bob")

    assert exc_info.value.status_code == 403


def test_require_admin_rejects_token_without_role():
    # Token emitido sin rol (p. ej. un JWT viejo de antes del issue #28): default deny.
    token = create_access_token({"sub": "carol"})

    with pytest.raises(ForbiddenError):
        require_admin(token=token, username="carol")
