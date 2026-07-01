"""
安全模块：密码哈希与 JWT Token 管理
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
import bcrypt
from .config import settings


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希，返回不可逆的哈希值"""
    salt = bcrypt.gensalt()   # 生成随机salt
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_hours: Optional[int] = None) -> str:
    """
    创建 JWT 访问令牌
    :param data: 要编码到 token 中的负载数据（通常包含 user_id, username, roles）
    :param expires_hours: token 有效期（小时），默认使用配置值
    :return: 编码后的 JWT 字符串
    """
    to_encode = data.copy()
    expire_hours = expires_hours or settings.JWT_EXPIRATION_HOURS
    expire = datetime.utcnow() + timedelta(hours=expire_hours)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码 JWT Token，返回负载数据
    :param token: JWT 字符串
    :return: 解码后的字典，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
