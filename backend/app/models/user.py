"""
用户模型：系统用户表
"""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base


class User(Base):
    """用户表 —— 存储所有系统用户的基本信息"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True, comment="用户名")
    password_hash = Column(String(256), nullable=False, comment="bcrypt 密码哈希")
    email = Column(String(128), comment="电子邮箱")
    avatar = Column(String(512), comment="头像 URL")
    status = Column(String(16), default="active", comment="用户状态: active/disabled")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
