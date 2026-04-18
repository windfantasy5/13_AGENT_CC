"""
用户相关Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    """用户注册"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=50)
    nickname: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserLogin(BaseModel):
    """用户登录"""
    username: str
    password: str


class UserUpdate(BaseModel):
    """用户信息更新"""
    nickname: Optional[str] = Field(None, max_length=100)
    avatar: Optional[str] = None
    hobbies: Optional[str] = None
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    phone: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None


class PasswordUpdate(BaseModel):
    """密码更新"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=50)


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    nickname: Optional[str]
    avatar: Optional[str]
    hobbies: Optional[str]
    gender: Optional[str]
    phone: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
