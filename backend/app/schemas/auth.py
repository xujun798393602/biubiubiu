from typing import Optional, List
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class UserInfo(BaseModel):
    id: str
    username: str
    role: str
    permissions: List[str]


class LoginResponse(BaseModel):
    token: str
    user: UserInfo


class ForgotPasswordRequest(BaseModel):
    username: str


class VerifyCodeRequest(BaseModel):
    username: str
    code: str


class ResetPasswordRequest(BaseModel):
    username: str
    code: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    email: str = Field(..., max_length=128)
    real_name: Optional[str] = Field(None, max_length=128)
