"""
标签模型：知识库标签分类系统
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, func
from app.core.database import Base

# 文档-标签关联表（多对多）
document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    """标签表 —— 用于文档分类和筛选"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True, comment="标签名，如 新能源/科技/金融/主板")
    color = Column(String(16), comment="标签颜色 HEX")
    description = Column(String(256), comment="标签描述")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
