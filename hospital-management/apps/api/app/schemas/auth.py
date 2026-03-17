from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class BootstrapAdminRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str


class MeResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=120)
    role: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=128)
