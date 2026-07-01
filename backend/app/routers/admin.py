"""
系统管理路由：用户管理、角色管理、操作日志、系统配置（M9 模块）
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import Optional
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role, user_roles
from app.models.log import OperationLog
from app.models.settings import SystemSetting
from app.schemas.user import (
    UserCreateRequest, UserUpdateRequest, UserListResponse,
    RoleCreateRequest, RoleResponse,
)
from app.middleware.auth import get_current_user, require_permission

router = APIRouter(prefix="/api/v1/admin", tags=["系统管理"])


# ============================================================
# 用户管理
# ============================================================

@router.get("/users", summary="获取用户列表")
def list_users(
    page: int = 1,
    page_size: int = 20,
    username: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:users")),
):
    """
    获取系统所有用户的列表，支持分页和筛选
    需要权限: admin:users
    """
    query = db.query(User)
    if username:
        query = query.filter(User.username.like(f"%{username}%"))
    if status:
        query = query.filter(User.status == status)

    total = query.count()
    users = query.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for u in users:
        roles = (
            db.query(Role.name)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .filter(user_roles.c.user_id == u.id)
            .all()
        )
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "status": u.status,
            "roles": [r[0] for r in roles],
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return {"code": 0, "data": {"total": total, "items": result, "page": page, "page_size": page_size}}


@router.post("/users", summary="创建用户")
def create_user(
    req: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:users")),
):
    """管理员创建新用户并分配角色"""
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(username=req.username, password_hash=hash_password(req.password), email=req.email)
    db.add(user)
    db.flush()

    # 分配角色
    for role_id in req.role_ids:
        role = db.query(Role).filter(Role.id == role_id).first()
        if role:
            db.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))

    db.commit()
    return {"code": 0, "data": {"id": user.id, "username": user.username}, "msg": "用户创建成功"}


@router.put("/users/{user_id}", summary="更新用户信息")
def update_user(
    user_id: int,
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:users")),
):
    """更新用户状态、邮箱或角色"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if req.email is not None:
        user.email = req.email
    if req.status is not None:
        user.status = req.status

    # 更新角色（先删后增）
    if req.role_ids is not None:
        db.execute(user_roles.delete().where(user_roles.c.user_id == user_id))
        for role_id in req.role_ids:
            db.execute(user_roles.insert().values(user_id=user_id, role_id=role_id))

    db.commit()
    return {"code": 0, "msg": "用户更新成功"}


@router.delete("/users/{user_id}", summary="删除用户")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:users")),
):
    """删除用户（不可删除自己）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    db.execute(user_roles.delete().where(user_roles.c.user_id == user_id))
    db.delete(user)
    db.commit()
    return {"code": 0, "msg": "用户已删除"}


# ============================================================
# 角色管理
# ============================================================

@router.get("/roles", summary="获取角色列表")
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:roles")),
):
    """获取所有角色及其权限配置"""
    roles = db.query(Role).all()
    return {
        "code": 0,
        "data": [
            {"id": r.id, "name": r.name, "display_name": r.display_name, "permissions": r.permissions or []}
            for r in roles
        ],
    }


@router.post("/roles", summary="创建角色")
def create_role(
    req: RoleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:roles")),
):
    """创建新角色并定义其权限"""
    existing = db.query(Role).filter(Role.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色名已存在")

    role = Role(name=req.name, display_name=req.display_name, permissions=req.permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"code": 0, "data": {"id": role.id, "name": role.name}, "msg": "角色创建成功"}


# ============================================================
# 操作日志
# ============================================================

@router.get("/logs", summary="获取操作日志")
def list_logs(
    page: int = 1,
    page_size: int = 30,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:logs")),
):
    """查询操作日志，支持按用户和操作类型筛选"""
    query = db.query(OperationLog)
    if user_id:
        query = query.filter(OperationLog.user_id == user_id)
    if action:
        query = query.filter(OperationLog.action == action)

    total = query.count()
    logs = query.order_by(desc(OperationLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "username": log.username,
                    "action": log.action,
                    "target_type": log.target_type,
                    "detail": log.detail,
                    "ip_address": log.ip_address,
                    "status": log.status,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        },
    }


# ============================================================
# 系统配置
# ============================================================

@router.get("/settings", summary="获取系统配置")
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:settings")),
):
    """获取所有系统配置项（API Key 等敏感值脱敏显示）"""
    settings_list = db.query(SystemSetting).all()
    result = {}
    for s in settings_list:
        val = s.setting_value
        # 对 API Key 类配置脱敏
        if "api_key" in s.setting_key.lower() and val:
            val = val[:8] + "****" + val[-4:] if len(val) > 12 else "****"
        result[s.setting_key] = {"value": val, "description": s.description}
    return {"code": 0, "data": result}


@router.put("/settings", summary="更新系统配置")
def update_settings(
    settings_map: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:settings")),
):
    """批量更新系统配置项"""
    for key, value in settings_map.items():
        setting = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
        if setting:
            setting.setting_value = str(value) if value is not None else ""
        else:
            db.add(SystemSetting(setting_key=key, setting_value=str(value) if value is not None else ""))
    db.commit()
    return {"code": 0, "msg": "配置更新成功"}
