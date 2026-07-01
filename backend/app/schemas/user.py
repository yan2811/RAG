"""
用户管理相关的 Pydantic 校验模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserCreateRequest(BaseModel):
    """管理员创建用户请求"""
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    password: str = Field(..., min_length=8, max_length=20, description="密码")
    email: Optional[str] = Field(None, max_length=128)
    role_ids: list[int] = Field(default_factory=list, description="分配的角色 ID 列表")


class UserUpdateRequest(BaseModel):
    """更新用户信息请求"""
    email: Optional[str] = Field(None, max_length=128)
    status: Optional[str] = Field(None, description="active/disabled")
    role_ids: Optional[list[int]] = Field(None, description="角色 ID 列表")


class UserListResponse(BaseModel):
    """用户列表响应"""
    id: int
    username: str
    email: Optional[str] = None
    status: str
    roles: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleCreateRequest(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=2, max_length=32, description="角色标识名")
    display_name: str = Field(..., max_length=64, description="角色显示名")
    permissions: list[str] = Field(default_factory=list, description="权限列表")


class RoleResponse(BaseModel):
    """角色信息响应"""
    id: int
    name: str
    display_name: str
    permissions: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
