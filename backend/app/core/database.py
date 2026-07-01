"""
数据库连接与会话管理模块
使用 SQLAlchemy 2.0 异步引擎连接 MySQL，提供依赖注入式的数据库会话
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# 创建数据库引擎（同步引擎，适用于 FastAPI 的同步 ORM 操作）
# echo=True 可在调试时打印 SQL 语句
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,           # 连接池大小
    pool_recycle=3600,      # 连接回收时间（秒）
    pool_pre_ping=True,     # 连接前检测可用性
    echo=settings.DEBUG,
    connect_args={"charset": "utf8mb4"},  # 确保 PyMySQL 使用 utf8mb4
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类，所有模型继承自此基类
Base = declarative_base()


def get_db():
    """
    FastAPI 依赖注入：提供数据库会话
    在请求结束时自动关闭会话，确保连接归还连接池

    使用方式：
        @app.get("/users")
        def list_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库表结构
    根据所有 ORM 模型定义自动创建表（仅在表不存在时创建，不会修改已有表）
    应在应用启动时调用
    """
    # 导入所有模型，确保它们被 Base 注册
    from app.models import user, role, document, session, log, settings as sys_settings, tag  # noqa: F401

    Base.metadata.create_all(bind=engine)
