from pydantic import BaseModel, EmailStr, Field
from app.models.models import UserRole

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole

class RegisterOut(BaseModel):
    user_id: int
    email: EmailStr
    role: UserRole
    verification_token: str
    detail: str

class VerifyIn(BaseModel): token: str
class LoginIn(BaseModel): email: EmailStr; password: str
class RefreshIn(BaseModel): refresh_token: str
class TokenOut(BaseModel): access_token: str; refresh_token: str; token_type: str = "bearer"
