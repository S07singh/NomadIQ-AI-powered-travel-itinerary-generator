from pydantic import EmailStr, Field, field_validator

from app.common.schemas import APIModel
from app.modules.users.schemas import UserOut


def _check_strength(v: str) -> str:
    if v.isdigit() or v.isalpha():
        raise ValueError("password must contain letters and numbers")
    return v


class RegisterRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=80)

    @field_validator("password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return _check_strength(v)


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(APIModel):
    refresh_token: str


class ChangePasswordRequest(APIModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return _check_strength(v)


class TokenPair(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class AuthResponse(APIModel):
    user: UserOut
    tokens: TokenPair
