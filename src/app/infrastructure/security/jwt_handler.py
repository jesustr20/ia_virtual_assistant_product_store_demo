from pwdlib import PasswordHash
from datetime import datetime, timedelta
import jwt
import os

SECRET_KEY = os.environ.get("SECRET_KEY")

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    hashed = password_hash.hash(password)
    return hashed

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])