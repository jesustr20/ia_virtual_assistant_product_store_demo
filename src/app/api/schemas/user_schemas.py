from pydantic import BaseModel, model_validator
from typing_extensions import Self

class UserCreate(BaseModel):
    username: str
    password: str
    password_repeat: str

    @model_validator(mode='after')
    def check_password_match(self) -> Self:
        if self.password != self.password_repeat:
            raise ValueError('Passwords do not match')
        return self

class UserLogin(BaseModel):
    username: str
    password: str