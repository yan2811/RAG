"""
文档模型：用户上传的财报文档元数据
"""
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, func
from app.core.database import Base


class Document(Base):
    """文档表 —— 记录所有上传的财报 PDF 文件元数据"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="上传者")
    file_name = Column(String(256), nullable=False, comment="原始文件名")
    file_path = Column(String(512), nullable=False, comment="服务器存储路径")
    file_size = Column(BigInteger, comment="文件大小（字节）")
    file_hash = Column(String(64), comment="SHA256 哈希，用于去重")
    doc_type = Column(String(32), comment="报告类型: annual_report/quarterly_report/prospectus/audit_report/other")
    company_name = Column(String(128), comment="公司名称")
    company_code = Column(String(16), comment="股票代码")
    fiscal_year = Column(Integer, comment="财年")
    fiscal_quarter = Column(Integer, comment="季度 1-4，年报填 4")
    page_count = Column(Integer, comment="总页数")
    parse_status = Column(String(16), default="pending", comment="解析状态: pending/parsing/completed/failed")
    chunk_count = Column(Integer, default=0, comment="分块数量")
    is_deleted = Column(Integer, default=0, comment="软删除标记: 0=正常 1=已删除")
    deleted_at = Column(DateTime, comment="删除时间（软删除）")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class Chunk(Base):
    """文档分块表 —— 记录每个文档 chunk 的索引信息"""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False, comment="chunk 序号")
    chunk_type = Column(String(16), default="text", comment="类型: text/table/indicator")
    section_title = Column(String(256), comment="所属章节标题")
    content = Column(String(8192), nullable=False, comment="chunk 文本内容")
    content_hash = Column(String(64), comment="内容哈希，用于增量更新去重")
    page_start = Column(Integer, comment="起始页码")
    page_end = Column(Integer, comment="结束页码")
    token_count = Column(Integer, comment="token 数量")
    chroma_id = Column(String(128), comment="ChromaDB 中对应向量 ID")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class FinancialMetric(Base):
    """财务指标表 —— 结构化的财务指标数据，支持精确查询"""
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    company_code = Column(String(16), nullable=False, comment="股票代码")
    fiscal_year = Column(Integer, nullable=False, comment="财年")
    fiscal_quarter = Column(Integer, default=4, comment="季度")
    metric_name = Column(String(64), nullable=False, comment="指标名: revenue/net_profit/gross_margin/roe/roa/...")
    metric_value = Column(String(32), comment="指标值（保留字符串以兼容不同格式）")
    metric_unit = Column(String(16), comment="单位: yuan/wan_yuan/yi_yuan/percent")
    yoy_change = Column(String(32), comment="同比变化(%)")
    source_section = Column(String(256), comment="数据来源章节")
    source_page = Column(Integer, comment="来源页码")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class DocumentVersion(Base):
    """文档版本表 —— 支持同公司同年度多版本文档管理"""
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1, comment="版本号")
    file_path = Column(String(512), nullable=False, comment="版本文件路径")
    change_note = Column(String(512), comment="变更说明")
    is_current = Column(Integer, default=1, comment="是否当前版本: 1=是 0=否")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
