"""
JWT 认证中间件：提供 FastAPI 依赖注入式的身份验证和权限校验
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.role import Role, user_roles

# HTTP Bearer Token 解析器
security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    从请求头中解析 JWT Token，返回当前登录用户
    所有需要登录的接口都应依赖此函数
    """
    token = credentials.credentials   # 从 header 拿 Bearer Token
    payload = decode_access_token(token)   # 解密 JWT 拿到 user_id
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中缺少用户标识",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if user.status == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员",
        )

    return user


def require_permission(permission: str):
    """
    权限校验装饰器工厂：检查当前用户是否具有指定权限
    使用方式：
        @app.get("/admin/users")
        def list_users(user=Depends(require_permission("admin:users"))):
            ...

    :param permission: 权限标识，如 "admin:users"、"doc:upload"
    """

    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        # 查询用户的所有角色及其权限
        roles = (
            db.query(Role)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .filter(user_roles.c.user_id == current_user.id)
            .all()
        )

        all_permissions = []
        for role in roles:
            if role.permissions:
                all_permissions.extend(role.permissions)

        # 超级管理员拥有所有权限（role.name == "super_admin"）
        if any(r.name == "super_admin" for r in roles):
            return current_user

        if permission not in all_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要权限: {permission}",
            )

        return current_user

    return permission_checker


def get_user_permissions(user: User, db: Session) -> list[str]:
    """获取用户的所有权限列表"""
    roles = (
        db.query(Role)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .filter(user_roles.c.user_id == user.id)
        .all()
    )
    perms = []
    for role in roles:
        if role.permissions:
            perms.extend(role.permissions)
    return list(set(perms))


def get_user_roles(user: User, db: Session) -> list[str]:
    """获取用户的所有角色名列表"""
    roles = (
        db.query(Role)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .filter(user_roles.c.user_id == user.id)
        .all()
    )
    return [r.name for r in roles]
