"""
角色与权限模型：RBAC 权限系统的核心表
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Table, func
from app.core.database import Base

# 用户-角色关联表（多对多）
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    """角色表 —— 定义系统角色及其权限集合"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), nullable=False, unique=True, comment="角色标识名，如 super_admin/admin/user/guest")
    display_name = Column(String(64), comment="角色显示名")
    permissions = Column(JSON, comment="权限列表 JSON，如 ['doc:upload','doc:delete','admin:users']")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
