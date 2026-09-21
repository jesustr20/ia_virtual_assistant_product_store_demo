from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.auth_service import AuthService
from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.infrastructure.security.jwt_handler import (
    decode_access_token,
    hash_password,
    verify_password,
)


def test_register_raises_when_username_exists():
    repo = Mock()
    repo.get_by_username.return_value = object()
    service = AuthService(repo)

    with pytest.raises(UserAlreadyExistsError):
        service.register("alice", "secret-pass")


def test_register_hashes_password_before_create_user():
    repo = Mock()
    repo.get_by_username.return_value = None
    repo.count_users.return_value = 0
    service = AuthService(repo)

    service.register("alice", "plaintext-pass")

    # El username, el hash y el rol llegan como args posicionales a create_user.
    username, hashed, role = repo.create_user.call_args.args
    assert username == "alice"
    # La contraseña en texto plano NUNCA debe guardarse.
    assert hashed != "plaintext-pass"
    # Y debe verificar contra el texto plano original.
    assert verify_password("plaintext-pass", hashed)


def test_register_first_user_is_admin():
    repo = Mock()
    repo.get_by_username.return_value = None
    repo.count_users.return_value = 0
    service = AuthService(repo)

    service.register("alice", "secret-pass")

    _, _, role = repo.create_user.call_args.args
    assert role == "admin"


def test_register_subsequent_user_gets_user_role():
    repo = Mock()
    repo.get_by_username.return_value = None
    repo.count_users.return_value = 3
    service = AuthService(repo)

    service.register("bob", "secret-pass")

    _, _, role = repo.create_user.call_args.args
    assert role == "user"


def test_login_raises_for_wrong_password():
    repo = Mock()
    repo.get_by_username.return_value = SimpleNamespace(
        username="alice", hashed_password=hash_password("correct-pass")
    )
    service = AuthService(repo)

    with pytest.raises(InvalidCredentialsError):
        service.login("alice", "wrong-pass")


def test_login_raises_for_nonexistent_user():
    repo = Mock()
    repo.get_by_username.return_value = None
    service = AuthService(repo)

    with pytest.raises(InvalidCredentialsError):
        service.login("nobody", "whatever")


def test_login_returns_token_for_correct_credentials():
    repo = Mock()
    repo.get_by_username.return_value = SimpleNamespace(
        username="alice", hashed_password=hash_password("correct-pass"), role="admin"
    )
    service = AuthService(repo)

    token = service.login("alice", "correct-pass")

    assert isinstance(token, str) and token
    # El token debe decodificarse y llevar el subject y el rol correctos.
    payload = decode_access_token(token)
    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"
