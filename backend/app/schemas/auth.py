"""
认证相关的 Pydantic 校验模型
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=64, description="用户名，3-64 字符")
    password: str = Field(..., min_length=8, max_length=20, description="密码，8-20 字符，需包含字母和数字")
    email: Optional[str] = Field(None, max_length=128, description="电子邮箱（选填）")


class LoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=1, max_length=64, description="密码")
    captcha_id: Optional[str] = Field(None, description="验证码 ID")
    captcha_code: Optional[str] = Field(None, description="验证码输入值")


class TokenResponse(BaseModel):
    """登录成功后返回的 Token 信息"""
    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="有效期（秒）")
    user: "UserInfo"


class UserInfo(BaseModel):
    """用户基本信息"""
    id: int
    username: str
    email: Optional[str] = None
    avatar: Optional[str] = None
    status: str
    roles: list[str] = Field(default_factory=list, description="角色标识名列表")
    permissions: list[str] = Field(default_factory=list, description="权限列表")

    class Config:
        from_attributes = True
