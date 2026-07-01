"""
系统配置与报告模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, func
from app.core.database import Base


class SystemSetting(Base):
    """系统配置表 —— 键值对形式的灵活配置存储"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(64), nullable=False, unique=True, comment="配置键，如 deepseek_api_key/chunk_size/logo_url")
    setting_value = Column(Text, comment="配置值")
    description = Column(String(256), comment="配置说明")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class Report(Base):
    """报告表 —— AI 生成的财务分析报告"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="生成者")
    company_code = Column(String(16), nullable=False, comment="股票代码")
    company_name = Column(String(128), comment="公司名称")
    fiscal_year = Column(Integer, nullable=False, comment="财年")
    report_type = Column(String(16), default="annual", comment="报告类型: annual/quarterly/comparison")
    content_md = Column(Text, comment="Markdown 格式报告内容")
    file_path = Column(String(512), comment="生成的 PDF 文件路径")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
