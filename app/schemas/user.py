from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    email: Optional[EmailStr] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    is_privacy_mode: bool
    auto_delete_days: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserInDB(UserResponse):
    hashed_password: str

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

class TokenVerify(BaseModel):
    token: str

class EmailRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
