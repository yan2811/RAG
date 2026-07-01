"""
文档管理相关的 Pydantic 校验模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """文档上传成功后的响应"""
    document_id: int
    file_name: str
    file_size: int
    parse_status: str


class DocumentListItem(BaseModel):
    """文档列表项"""
    id: int
    file_name: str
    file_size: int
    doc_type: Optional[str] = None
    company_name: Optional[str] = None
    company_code: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    page_count: Optional[int] = None
    parse_status: str
    chunk_count: int
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    """文档详情"""
    id: int
    file_name: str
    file_size: int
    doc_type: Optional[str] = None
    company_name: Optional[str] = None
    company_code: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    page_count: Optional[int] = None
    parse_status: str
    chunk_count: int
    created_at: Optional[str] = None
    chunks: Optional[list] = []

    class Config:
        from_attributes = True


class ParseProgressResponse(BaseModel):
    """解析进度响应"""
    document_id: int
    parse_status: str
    progress: Optional[str] = None  # 进度描述，如 "正在提取文本..."
