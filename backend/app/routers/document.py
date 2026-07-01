"""
文档管理路由（M1 模块）
文档上传、列表查询、详情查看、删除、解析触发、进度查询
"""
import os
import uuid
import json

import logger
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.models.document import Document, Chunk
from app.middleware.auth import get_current_user, require_permission
from app.services.document_service import calculate_file_hash, parse_document
from app.services.log_service import record_operation
from app.schemas.document import DocumentListItem, DocumentDetailResponse, ParseProgressResponse

router = APIRouter(prefix="/api/v1/documents", tags=["文档管理"])


def _get_client_ip(request: Request) -> str:
    """从请求中获取客户端 IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/upload", summary="上传财报 PDF 文档")
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="财报 PDF 文件"),
    company_code: Optional[str] = Form(None, description="股票代码，如 002594"),
    fiscal_year: Optional[int] = Form(None, description="财年，如 2024"),
    fiscal_quarter: Optional[int] = Form(4, description="季度 1-4"),
    doc_type: Optional[str] = Form("annual_report", description="报告类型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("doc:upload")),
):
    """
    上传财报 PDF 文件并触发异步解析
    文件会被保存到 UPLOAD_DIR，元数据写入 documents 表
    """
    # 校验文件格式
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持上传 PDF 格式文件")

    # 校验文件大小（默认 100MB）
    file.file.seek(0, 2)  # 移动到文件末尾获取大小
    file_size = file.file.tell()
    file.file.seek(0)  # 重置指针

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小不能超过 {settings.MAX_UPLOAD_SIZE // 1048576}MB")

    # 确保上传目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # 生成唯一文件名并保存
    file_ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{file_ext}"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    content = await file.read()
    with open(stored_path, "wb") as f:
        f.write(content)

    # 计算文件哈希用于去重
    file_hash = calculate_file_hash(stored_path)

    # 检查是否已存在相同文件
    existing = db.query(Document).filter(Document.file_hash == file_hash, Document.is_deleted == 0).first()
    if existing:
        os.remove(stored_path)  # 删除重复文件
        raise HTTPException(status_code=400, detail=f"该文件已存在（文档 ID: {existing.id}）")

    # 创建文档记录
    document = Document(
        user_id=current_user.id,
        file_name=file.filename,
        file_path=stored_path,
        file_size=file_size,
        file_hash=file_hash,
        doc_type=doc_type,
        company_code=company_code,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        parse_status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # 记录操作日志
    record_operation(
        db, current_user.id, current_user.username,
        action="upload", target_type="document", target_id=document.id,
        detail={"file_name": file.filename, "file_size": file_size},
        ip_address=_get_client_ip(request),
    )

    # 异步触发解析（简单场景直接同步解析）
    try:
        result = parse_document(db, document.id)
        # 更新公司名称（从文件名推断）
        company_name = os.path.splitext(file.filename)[0]
        if company_code:
            document.company_name = company_name
            db.commit()
    except Exception as e:
        document.parse_status = "failed"
        db.commit()

    return {
        "code": 0,
        "data": {
            "document_id": document.id,
            "file_name": document.file_name,
            "file_size": document.file_size,
            "parse_status": document.parse_status,
        },
        "msg": "上传成功",
    }


@router.get("", summary="获取文档列表")
def list_documents(
    page: int = 1,
    page_size: int = 20,
    parse_status: Optional[str] = None,
    company_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户的文档列表，支持按解析状态和股票代码筛选
    """
    query = db.query(Document).filter(
        Document.is_deleted == 0,
        Document.user_id == current_user.id,  # 用户只能看自己的文档
    )
    if parse_status:
        query = query.filter(Document.parse_status == parse_status)
    if company_code:
        query = query.filter(Document.company_code == company_code)

    total = query.count()
    documents = query.order_by(desc(Document.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    items = [
        {
            "id": d.id,
            "file_name": d.file_name,
            "file_size": d.file_size,
            "doc_type": d.doc_type,
            "company_name": d.company_name,
            "company_code": d.company_code,
            "fiscal_year": d.fiscal_year,
            "fiscal_quarter": d.fiscal_quarter,
            "page_count": d.page_count,
            "parse_status": d.parse_status,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in documents
    ]

    return {"code": 0, "data": {"total": total, "items": items, "page": page, "page_size": page_size}}


@router.get("/{document_id}", summary="获取文档详情")
def get_document_detail(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取单个文档的详细信息，包含分块列表预览
    """
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.is_deleted == 0,
        Document.user_id == current_user.id,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")

    # 查询该文档的分块列表
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()

    return {
        "code": 0,
        "data": {
            "id": doc.id,
            "file_name": doc.file_name,
            "file_size": doc.file_size,
            "doc_type": doc.doc_type,
            "company_name": doc.company_name,
            "company_code": doc.company_code,
            "fiscal_year": doc.fiscal_year,
            "fiscal_quarter": doc.fiscal_quarter,
            "page_count": doc.page_count,
            "parse_status": doc.parse_status,
            "chunk_count": doc.chunk_count,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "chunks": [
                {
                    "id": c.id,
                    "chunk_index": c.chunk_index,
                    "chunk_type": c.chunk_type,
                    "section_title": c.section_title,
                    "content_preview": c.content[:200] + "..." if len(c.content) > 200 else c.content,
                    "content_full": c.content,
                    "page_start": c.page_start,
                }
                for c in chunks
            ],
        },
    }


@router.get("/{document_id}/fulltext", summary="获取文档完整文本内容")
def get_document_fulltext(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档的全部文本内容（合并所有 chunk，按章节排列）"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.is_deleted == 0,
        Document.user_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")

    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()

    # 按章节组织内容
    sections = []
    for c in chunks:
        sections.append({
            "section_title": c.section_title or "正文",
            "chunk_type": c.chunk_type,
            "page_start": c.page_start,
            "content": c.content,
        })

    # 合并为完整文本
    full_text = "\n\n".join([
        f"## {s['section_title']}（第{s['page_start']}页）\n\n{s['content']}"
        for s in sections
    ])

    return {
        "code": 0,
        "data": {
            "document_id": doc.id,
            "file_name": doc.file_name,
            "company_code": doc.company_code,
            "fiscal_year": doc.fiscal_year,
            "sections": sections,
            "full_text": full_text,
        },
    }


@router.get("/{document_id}/file", summary="下载/查看原始PDF文件")
def download_original_file(
    document_id: int,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """直接返回原始 PDF 文件，支持浏览器内嵌预览（token 可通过 query 参数传递）"""
    from fastapi.responses import FileResponse
    from app.core.security import decode_access_token

    # 支持 query 参数 token（浏览器直接打开时）
    user_id = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("user_id")

    if user_id is None:
        raise HTTPException(status_code=401, detail="请提供有效的 token 参数")

    doc = db.query(Document).filter(
        Document.id == document_id, Document.is_deleted == 0,
        Document.user_id == user_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 解析文件路径（相对于项目 backend 目录）
    file_path = doc.file_path
    if not os.path.isabs(file_path):
        import pathlib
        base_dir = pathlib.Path(__file__).parent.parent.parent  # backend/
        file_path = str(base_dir / file_path.lstrip('./'))

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    # 使用 ASCII 安全的文件名避免编码错误
    safe_filename = doc.file_name.encode('ascii', errors='ignore').decode('ascii') or 'document.pdf'
    return FileResponse(file_path, media_type="application/pdf", filename=safe_filename)


@router.delete("/{document_id}", summary="软删除文档")
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("doc:delete")),
):
    """
    软删除文档：标记 is_deleted=1，30 天内可恢复
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.is_deleted == 0).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    doc.is_deleted = 1
    from datetime import datetime
    doc.deleted_at = datetime.now()
    db.commit()

    record_operation(
        db, current_user.id, current_user.username,
        action="delete", target_type="document", target_id=document_id,
        detail={"file_name": doc.file_name},
        ip_address=_get_client_ip(request),
    )

    return {"code": 0, "msg": "文档已删除"}


@router.get("/{document_id}/status", summary="查询文档解析进度")
def get_parse_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询文档的解析状态
    前端可轮询此接口获取解析进度
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.is_deleted == 0).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    return {
        "code": 0,
        "data": {
            "document_id": doc.id,
            "parse_status": doc.parse_status,
            "page_count": doc.page_count,
            "chunk_count": doc.chunk_count,
        },
    }


@router.post("/{document_id}/parse", summary="AI 智能分节")
def trigger_parse(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("doc:upload")),
):
    """AI 智能分节：收集现有文本 → DeepSeek 分析 → 重新切分语义章节"""
    doc = db.query(Document).filter(Document.id == document_id, Document.is_deleted == 0).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    old_chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
    if not old_chunks:
        # 旧chunk丢失，重新从PDF解析
        from app.services.document_service import parse_document
        result = parse_document(db, document_id)
        old_chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
        if not old_chunks:
            raise HTTPException(status_code=400, detail="PDF解析失败，请重新上传文档")

    full_text = "\n\n".join([c.content for c in old_chunks])
    section_count = ai_rechunk_document(db, doc, full_text)

    return {
        "code": 0,
        "data": {"chunk_count": section_count},
        "msg": f"AI 智能分节完成，共 {section_count} 个章节",
    }


def ai_rechunk_document(db: Session, doc: Document, full_text: str) -> int:
    """使用 DeepSeek AI 分析文档结构并重新分块"""
    from app.services.llm_service import generate_sync
    import hashlib

    # ===== Step 0: 保存表格 chunks（AI 不处理表格） =====
    old_table_chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == doc.id, Chunk.chunk_type == "table")
        .order_by(Chunk.chunk_index)
        .all()
    )
    saved_tables = [
        {
            "chunk_index": t.chunk_index,
            "section_title": t.section_title,
            "content": t.content,
            "page_start": t.page_start,
        }
        for t in old_table_chunks
    ]

    # ===== Step 1: 发送文本给 AI 做语义分节 =====
    # 取更长文本，确保重点数据不丢失
    text_for_ai = full_text[:30000] if len(full_text) > 30000 else full_text

    prompt = f"""你是财报分析专家。请将下文按以下维度拆分为独立章节，格式：章节标题|内容片段（保留原文关键数据和表格，不要改写）
维度：公司简介、业务收入、成本与费用、资产负债、现金流、财务指标、风险因素、总结展望
规则：
- 每个维度至少一个章节，把原文相关段落归入对应章节，保留原文数字和表格文本
- 格式：章节标题|内容（一行一个章节，标题和内容用 | 分隔）
- 内容至少 50 字

{text_for_ai}"""

    result = generate_sync(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=8000,  # 增大输出上限
    )

    # ===== Step 2: 解析 AI 返回的章节 =====
    new_chunks = []
    if result and "|" in result:
        for line in result.strip().split("\n"):
            line = line.strip()
            if "|" not in line:
                continue
            parts = line.split("|", 1)
            if len(parts) != 2:
                continue
            title, content = parts[0].strip(), parts[1].strip()
            if len(content) < 30:
                continue
            new_chunks.append({"title": title, "content": content})

    # 如果 AI 返回结果太少（<3），说明出了问题，回退不做删除
    if len(new_chunks) < 3:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(f"AI 分节仅返回 {len(new_chunks)} 个章节，可能失败，保留原有 chunks")
        return len(old_table_chunks) + len(
            db.query(Chunk).filter(
                Chunk.document_id == doc.id, Chunk.chunk_type == "text"
            ).all()
        )

    # ===== Step 3: 删除旧 chunks，写入新章节 + 还原表格 =====
    db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
    db.flush()

    section_count = 0

    # 写入文字章节
    for ch in new_chunks:
        section_count += 1
        chunk = Chunk(
            document_id=doc.id,
            chunk_index=section_count,
            chunk_type="text",
            section_title=ch["title"],
            content=ch["content"],
            content_hash=hashlib.md5(ch["content"].encode()).hexdigest(),
            page_start=section_count,
        )
        db.add(chunk)

    # 还原表格 chunks（按原来顺序追加在后面）
    for t in saved_tables:
        section_count += 1
        chunk = Chunk(
            document_id=doc.id,
            chunk_index=section_count,
            chunk_type="table",
            section_title=t["section_title"],
            content=t["content"],
            page_start=t["page_start"],
        )
        db.add(chunk)

    doc.chunk_count = section_count
    doc.parse_status = "completed"
    db.commit()
    return section_count


def _auto_tag_document(db: Session, doc: Document, full_text: str):
    """AI 自动打标签"""
    from app.services.llm_service import generate_sync
    from app.models.tag import Tag, document_tags

    sample = full_text[:2000]
    prompt = f"分析此财报，提取3-5个标签(2-4字)，只返回JSON数组如[\"新能源\",\"高增长\"]。\n{sample[:1500]}"

    result = generate_sync(messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=80)

    if result:
        try:
            import json as j
            tags = j.loads(result.strip().strip("```").strip("json").strip())
            if not isinstance(tags, list):
                tags = []
        except:
            tags = []

        db.query(document_tags).filter(document_tags.c.document_id == doc.id).delete()

        for tag_name in tags[:5]:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, color="#409EFF")
                db.add(tag)
                db.flush()
            db.execute(document_tags.insert().values(document_id=doc.id, tag_id=tag.id))

        if tags:
            db.commit()


def _auto_tag_document(db: Session, doc: Document, full_text: str):
    """AI 根据文档内容自动生成标签"""
    from app.services.llm_service import generate_sync
    from app.models.tag import Tag, document_tags

    # 截取前 3000 字给 AI 分析
    sample = full_text[:3000] if len(full_text) > 3000 else full_text

    prompt = f"""请分析以下财报文档，提取 3-5 个关键标签（每个2-4字），标签应涵盖行业、规模特征、财务特点等维度。
只返回 JSON 数组格式，如 ["新能源","汽车制造","高增长","龙头股"]，不要其他内容。

文档内容：
{sample[:2000]}"""

    result = generate_sync(messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=100)

    if result:
        try:
            import json as j
            # 清理可能的markdown标记
            cleaned = result.strip().strip("```").strip("json").strip()
            tags = j.loads(cleaned) if isinstance(j.loads(cleaned), list) else []
        except:
            tags = []

        # 清除旧标签关联
        db.query(document_tags).filter(document_tags.c.document_id == doc.id).delete()

        for tag_name in tags[:5]:
            # 查找或创建标签
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, color="#409EFF")
                db.add(tag)
                db.flush()
            db.execute(document_tags.insert().values(document_id=doc.id, tag_id=tag.id))

        if tags:
            db.commit()
            logger.info(f"AI 自动标签: {tags}")
