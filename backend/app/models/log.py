"""
操作日志模型：记录所有关键操作，用于安全审计
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from app.core.database import Base


class OperationLog(Base):
    """操作日志表 —— 审计追踪用"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, comment="操作用户 ID")
    username = Column(String(64), comment="操作用户名")
    action = Column(String(64), nullable=False, comment="操作类型: upload/delete/export/generate/login/logout/...")
    target_type = Column(String(32), comment="操作对象类型: document/session/report/...")
    target_id = Column(Integer, comment="操作对象 ID")
    detail = Column(JSON, comment="操作详情 JSON")
    ip_address = Column(String(45), comment="客户端 IP 地址")
    user_agent = Column(String(512), comment="客户端 User-Agent")
    status = Column(String(16), default="success", comment="操作结果: success/failure")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
