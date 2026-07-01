"""
操作日志服务：提供统一的日志记录接口
"""
from sqlalchemy.orm import Session
from app.models.log import OperationLog


def record_operation(
    db: Session,
    user_id: int,
    username: str,
    action: str,
    target_type: str = None,
    target_id: int = None,
    detail: dict = None,
    ip_address: str = None,
    user_agent: str = None,
    status: str = "success",
):
    """
    记录一条操作日志到数据库
    :param db: 数据库会话
    :param user_id: 操作用户 ID
    :param username: 操作用户名
    :param action: 操作类型，如 upload/login/delete/export
    :param target_type: 操作对象类型，如 document/session
    :param target_id: 操作对象 ID
    :param detail: 操作详情（JSON 格式）
    :param ip_address: 客户端 IP
    :param user_agent: 客户端浏览器标识
    :param status: 操作结果，success 或 failure
    """
    log = OperationLog(
        user_id=user_id,
        username=username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
    )
    db.add(log)
    db.commit()
