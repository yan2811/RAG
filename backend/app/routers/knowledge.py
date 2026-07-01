"""
知识库管理路由（M3 模块）
知识库概览、标签管理、版本管理、批量操作
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List
from pydantic import BaseModel, Field
from app.core.database import get_db


class CreateTagRequest(BaseModel):
    name: str = Field(..., description="标签名")
    color: Optional[str] = Field("#409EFF", description="标签颜色 HEX")
    description: Optional[str] = Field(None, description="标签描述")
from app.models.user import User
from app.models.document import Document, Chunk, DocumentVersion
from app.models.tag import Tag, document_tags
from app.models.session import Session as ChatSession, Message
from app.models.settings import Report
from app.middleware.auth import get_current_user, require_permission
from app.services.vector_store import get_collection_stats
from app.services.embedding_service import embed_texts
from app.services.vector_store import add_chunks, delete_document_chunks, get_collection
import re

router = APIRouter(prefix="/api/v1/knowledge", tags=["知识库管理"])


# ============================================================
# 金融专业知识库（预置知识）
# ============================================================

FINANCIAL_KNOWLEDGE = [
    {
        "title": "财务分析核心指标体系",
        "content": (
            "财务分析核心指标体系包括五大类：\n"
            "一、盈利能力指标\n"
            "  1. 毛利率 = (营业收入-营业成本)/营业收入，反映产品或服务的盈利能力，越高越好。制造业合理范围15%-40%。\n"
            "  2. 净利率 = 净利润/营业收入，反映企业最终获利能力。一般>5%为良好。\n"
            "  3. ROE（净资产收益率）= 净利润/股东权益，衡量股东资金使用效率。>10%为良好，>20%为优秀。\n"
            "  4. ROA（总资产收益率）= 净利润/总资产，衡量总资产的获利能力。>5%为良好。\n"
            "  5. 基本每股收益(EPS) = 净利润/总股本，投资者最关注的指标之一。\n\n"
            "二、偿债能力指标\n"
            "  1. 资产负债率 = 总负债/总资产，衡量财务杠杆水平。一般40%-60%为合理，>70%需警惕。\n"
            "  2. 流动比率 = 流动资产/流动负债，衡量短期偿债能力。>1.5为安全，<1为危险。\n"
            "  3. 速动比率 = (流动资产-存货)/流动负债，更严格的短期偿债指标。>1为良好。\n"
            "  4. 利息保障倍数 = EBIT/利息费用，衡量支付利息的能力。>3为安全。\n\n"
            "三、营运能力指标\n"
            "  1. 应收账款周转率 = 营业收入/应收账款平均余额，衡量回款效率。越高越好，通常>6次/年为良好。\n"
            "  2. 存货周转率 = 营业成本/存货平均余额，衡量库存管理效率。行业差异大，制造业>3次/年为良好。\n"
            "  3. 总资产周转率 = 营业收入/总资产，衡量资产使用效率。>0.5次/年为良好。\n\n"
            "四、成长能力指标\n"
            "  1. 营业收入增长率 = (本期营收-上期营收)/上期营收，>10%为高增长，0-10%为稳健增长，<0为衰退。\n"
            "  2. 净利润增长率，>15%为优秀。\n"
            "  3. 总资产增长率，反映企业规模扩张速度。\n\n"
            "五、现金流指标\n"
            "  1. 经营活动现金流净额，最核心的现金流指标。>净利润说明盈利质量高。\n"
            "  2. 自由现金流 = 经营现金流 - 资本支出，反映可自由支配的现金。\n"
            "  3. 现金流/营业收入比率，>10%为良好。"
        ),
    },
    {
        "title": "财务报表结构与阅读方法",
        "content": (
            "上市公司的财务报告主要包括以下几大部分：\n\n"
            "一、审计报告\n"
            "由独立会计师事务所出具，分为：标准无保留意见（最好）、保留意见、否定意见、无法表示意见。\n"
            "如出现非标准意见，需高度警惕公司财务问题。\n\n"
            "二、管理层讨论与分析（MD&A）\n"
            "最重要但常被忽略的部分。管理层解释业绩变动的原因、行业趋势、未来展望。\n"
            "应重点关注：\n"
            "  1. 收入变动的原因（量价分析）\n"
            "  2. 成本变动的驱动因素\n"
            "  3. 未来战略规划与风险提示\n\n"
            "三、四大财务报表\n"
            "  1. 资产负债表(Balance Sheet)：反映某一时点(年末/季末)的财务状况。核心公式：资产 = 负债 + 所有者权益。\n"
            "  2. 利润表(Income Statement)：反映一定期间的经营成果。核心公式：收入 - 成本费用 = 利润。\n"
            "  3. 现金流量表(Cash Flow Statement)：反映现金流入流出。分经营活动、投资活动、筹资活动三类。\n"
            "  4. 所有者权益变动表：反映股东权益的增减变化。\n\n"
            "四、报表附注\n"
            "对报表中数字的补充说明，包括：\n"
            "  1. 会计政策和会计估计变更\n"
            "  2. 关联交易披露\n"
            "  3. 或有事项（未决诉讼、对外担保等）\n"
            "  4. 重大资产重组信息\n\n"
            "五、财务分析常用方法\n"
            "  1. 趋势分析：同一公司连续多年同一指标的变化\n"
            "  2. 结构分析：各组成部分占总额的百分比\n"
            "  3. 比率分析：利用各种财务比率评估企业\n"
            "  4. 比较分析：与同行或行业平均对比\n"
            "  5. 杜邦分析：ROE = 净利率 × 资产周转率 × 权益乘数"
        ),
    },
    {
        "title": "常见财务造假与风险识别",
        "content": (
            "识别财务造假的常见方法：\n\n"
            "一、收入造假信号\n"
            "  1. 应收账款增速显著高于营业收入增速（可能是虚增收入）\n"
            "  2. 经营活动现金流长期低于净利润（利润质量差）\n"
            "  3. 毛利率远超同行平均水平且无合理解释\n"
            "  4. 关联交易收入占比过高\n"
            "  5. 境外收入占比高但难以核实\n\n"
            "二、资产造假信号\n"
            "  1. 存货快速增长同时毛利率下降（可能隐藏成本）\n"
            "  2. 在建工程长期挂账不转固（可能虚增资产）\n"
            "  3. 商誉占净资产比例过高（>30%需警惕减值风险）\n"
            "  4. 应收账款坏账计提比例低于同行\n\n"
            "三、负债隐藏信号\n"
            "  1. 表外负债（担保、承诺等）金额巨大\n"
            "  2. 过于复杂的股权结构\n"
            "  3. 频繁更换会计师事务所\n\n"
            "四、其他预警信号\n"
            "  1. 大股东高比例质押（>50%需警惕）\n"
            "  2. 分红政策异常（盈利却长期不分红）\n"
            "  3. 董监高频繁离职\n"
            "  4. 收到交易所问询函\n"
            "  5. 亏损或经营异常时仍大规模扩张"
        ),
    },
    {
        "title": "行业分析框架与比较方法",
        "content": (
            "行业分析的核心框架：\n\n"
            "一、波特五力模型\n"
            "  1. 现有竞争者的竞争程度：市场份额分布、价格战程度\n"
            "  2. 潜在进入者的威胁：行业壁垒（资金/技术/政策）、规模经济效应\n"
            "  3. 替代品的威胁：替代品性价比、转换成本\n"
            "  4. 供应商的议价能力：供应商集中度、原材料可替代性\n"
            "  5. 买方的议价能力：客户集中度、产品差异化程度\n\n"
            "二、行业生命周期分析\n"
            "  1. 导入期：技术不成熟、市场小、亏损为主\n"
            "  2. 成长期：市场规模快速扩大、竞争加剧、利润增长\n"
            "  3. 成熟期：市场饱和、竞争格局稳定、利润稳定\n"
            "  4. 衰退期：市场萎缩、竞争减少、利润下降\n\n"
            "三、跨公司对比要点\n"
            "  1. 选择同一行业的可比公司进行对比\n"
            "  2. 对比指标：毛利率、净利率、ROE、资产负债率、营收增长率\n"
            "  3. 注意公司规模差异（不同体量的公司财务特征不同）\n"
            "  4. 注意会计政策差异（不同公司的收入确认、折旧方法可能不同）\n"
            "  5. 进行多年趋势对比，避免单一年度的异常值误导\n\n"
            "四、新能源汽车行业特点（示例）\n"
            "  1. 毛利率：龙头公司25%左右，二三线15-20%\n"
            "  2. 研发费用率：行业均值5-6%，领先企业通常>5%\n"
            "  3. ROE：优秀企业>15%\n"
            "  4. 资产负债率：50-65%较为常见\n"
            "  5. 行业关键竞争要素：技术路线、产能规模、成本控制、品牌力、全球化布局"
        ),
    },
]


@router.post("/import-finance-knowledge", summary="导入金融专业知识到知识库")
def import_finance_knowledge(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("kb:manage")),
):
    """
    将预置的金融专业知识（财务分析体系、报表阅读方法、风险识别等）
    导入到知识库中，作为 RAG 问答的基础知识补充
    这些知识会与用户上传的文档一起参与检索
    """
    from app.models.document import Document, Chunk
    from app.services.vector_store import add_chunks
    from app.services.embedding_service import embed_texts

    # 创建或获取"金融专业知识库"虚拟文档
    kdoc = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.doc_type == "knowledge_base",
        Document.company_code == "FINANCE_KB",
    ).first()

    if not kdoc:
        kdoc = Document(
            user_id=current_user.id,
            file_name="金融专业知识库",
            file_path="./knowledge/finance_knowledge",
            file_size=0,
            file_hash="finance_knowledge_base_v1",
            doc_type="knowledge_base",
            company_code="FINANCE_KB",
            company_name="金融专业知识库",
            fiscal_year=2026,
            parse_status="completed",
            page_count=len(FINANCIAL_KNOWLEDGE),
        )
        db.add(kdoc)
        db.flush()
    else:
        # 清除旧的分块
        db.query(Chunk).filter(Chunk.document_id == kdoc.id).delete()
        db.flush()

    # 创建分块
    chunks_created = 0
    texts, chunk_ids, metadatas = [], [], []
    for i, item in enumerate(FINANCIAL_KNOWLEDGE):
        chunk = Chunk(
            document_id=kdoc.id,
            chunk_index=i + 1,
            chunk_type="text",
            section_title=item["title"],
            content=item["content"],
            page_start=i + 1,
        )
        db.add(chunk)
        db.flush()
        texts.append(item["content"])
        chunk_ids.append(f"finance_kb_chunk_{kdoc.id}_{chunk.id}")
        metadatas.append({"document_id": kdoc.id, "section_title": item["title"], "chunk_type": "financial_knowledge"})
        chunks_created += 1

    # 向量化并存入 ChromaDB
    embeddings = embed_texts(texts)
    if embeddings:
        add_chunks(chunk_ids, texts, embeddings, metadatas)

    kdoc.chunk_count = chunks_created
    db.commit()

    return {
        "code": 0,
        "msg": f"金融专业知识导入成功：{chunks_created} 个知识点",
        "data": {
            "document_id": kdoc.id,
            "chunks_created": chunks_created,
            "topics": [item["title"] for item in FINANCIAL_KNOWLEDGE],
        },
    }


# ============================================================
# 知识库概览
# ============================================================

@router.get("/overview", summary="知识库概览统计")
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取知识库的整体统计信息：文档数、公司数、索引状态、存储用量
    """
    # 文档总数
    total_docs = db.query(func.count(Document.id)).filter(
        Document.is_deleted == 0,
        Document.user_id == current_user.id,
    ).scalar() or 0

    # 已完成解析的文档数
    completed_docs = db.query(func.count(Document.id)).filter(
        Document.is_deleted == 0,
        Document.user_id == current_user.id,
        Document.parse_status == "completed",
    ).scalar() or 0

    # 覆盖公司数
    companies = db.query(func.count(func.distinct(Document.company_code))).filter(
        Document.is_deleted == 0,
        Document.user_id == current_user.id,
        Document.company_code.isnot(None),
    ).scalar() or 0

    # Chunk 总数
    total_chunks = db.query(func.count(Chunk.id)).join(
        Document, Chunk.document_id == Document.id
    ).filter(
        Document.is_deleted == 0,
        Document.user_id == current_user.id,
    ).scalar() or 0

    # 向量统计
    vector_stats = get_collection_stats()

    # 年度分布
    year_dist = db.query(
        Document.fiscal_year,
        func.count(Document.id)
    ).filter(
        Document.is_deleted == 0,
        Document.user_id == current_user.id,
        Document.fiscal_year.isnot(None),
    ).group_by(Document.fiscal_year).order_by(Document.fiscal_year.desc()).all()

    return {
        "code": 0,
        "data": {
            "total_documents": total_docs,
            "completed_documents": completed_docs,
            "total_companies": companies,
            "total_chunks": total_chunks,
            "total_vectors": vector_stats.get("total_vectors", 0),
            "year_distribution": [{"year": y, "count": c} for y, c in year_dist],
        },
    }


# ============================================================
# 标签管理
# ============================================================

@router.get("/tags", summary="获取标签列表")
def list_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有标签及其使用统计"""
    tags = db.query(Tag).all()
    result = []
    for t in tags:
        doc_count = db.query(func.count(document_tags.c.document_id)).filter(
            document_tags.c.tag_id == t.id
        ).scalar() or 0
        result.append({
            "id": t.id,
            "name": t.name,
            "color": t.color or "#409EFF",
            "description": t.description,
            "document_count": doc_count,
        })
    return {"code": 0, "data": result}


@router.post("/tags", summary="创建标签")
def create_tag(
    req: CreateTagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("kb:manage")),
):
    """创建新标签（POST JSON Body）"""
    existing = db.query(Tag).filter(Tag.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="标签名已存在")

    tag = Tag(name=req.name, color=req.color, description=req.description)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return {"code": 0, "data": {"id": tag.id, "name": tag.name}, "msg": "标签创建成功"}


@router.delete("/tags/{tag_id}", summary="删除标签")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("kb:manage")),
):
    """删除标签同时清除关联关系"""
    db.query(document_tags).filter(document_tags.c.tag_id == tag_id).delete()
    db.query(Tag).filter(Tag.id == tag_id).delete()
    db.commit()
    return {"code": 0, "msg": "标签已删除"}


@router.post("/documents/{doc_id}/tags", summary="为文档添加标签")
def add_document_tags(
    doc_id: int,
    tag_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("kb:manage")),
):
    """批量为文档设置标签"""
    # 清除旧标签
    db.query(document_tags).filter(document_tags.c.document_id == doc_id).delete()
    # 添加新标签
    for tid in tag_ids:
        db.execute(document_tags.insert().values(document_id=doc_id, tag_id=tid))
    db.commit()
    return {"code": 0, "msg": "标签更新成功"}


# ============================================================
# 文档版本管理
# ============================================================

@router.get("/documents/{doc_id}/versions", summary="获取文档版本列表")
def list_versions(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取某文档的所有历史版本"""
    versions = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc_id
    ).order_by(desc(DocumentVersion.version_number)).all()

    return {
        "code": 0,
        "data": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "file_path": v.file_path,
                "change_note": v.change_note,
                "is_current": v.is_current,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


# ============================================================
# 向量索引管理
# ============================================================

@router.post("/index/{doc_id}", summary="为文档构建向量索引")
def build_vector_index(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("kb:manage")),
):
    """
    对已解析完成的文档，提取所有 chunk 进行向量化并存入 ChromaDB
    """
    doc = db.query(Document).filter(Document.id == doc_id, Document.is_deleted == 0).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if doc.parse_status != "completed":
        raise HTTPException(status_code=400, detail="文档尚未解析完成")

    # 获取文档所有 chunk
    chunks = db.query(Chunk).filter(Chunk.document_id == doc_id).all()
    if not chunks:
        raise HTTPException(status_code=400, detail="文档没有分块内容")

    # 先删除旧向量
    delete_document_chunks(doc_id)

    # 批量向量化
    texts = [c.content for c in chunks]
    embeddings = embed_texts(texts)

    if embeddings is None:
        return {"code": -1, "msg": "Embedding 模型未就绪，请先安装 sentence-transformers"}

    # 存入 ChromaDB
    chunk_ids = [f"doc_{doc_id}_chunk_{c.id}" for c in chunks]
    metadatas = [
        {
            "document_id": doc_id,
            "chunk_id": c.id,
            "section_title": c.section_title or "",
            "chunk_type": c.chunk_type or "text",
            "page_start": c.page_start or 0,
            "company_code": doc.company_code or "",
            "fiscal_year": doc.fiscal_year or 0,
        }
        for c in chunks
    ]

    add_chunks(chunk_ids, texts, embeddings, metadatas)

    # 更新 chunk 的 chroma_id
    for i, chunk in enumerate(chunks):
        chunk.chroma_id = chunk_ids[i]
    db.commit()

    return {
        "code": 0,
        "msg": f"向量索引构建完成，共 {len(chunks)} 个向量",
        "data": {"chunk_count": len(chunks)},
    }


@router.post("/reindex", summary="全量重建向量索引")
def rebuild_all_index(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("kb:manage")),
):
    """对所有已解析完成的文档重新构建向量索引"""
    docs = db.query(Document).filter(
        Document.is_deleted == 0,
        Document.parse_status == "completed",
    ).all()

    total_chunks = 0
    for doc in docs:
        chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).all()
        if not chunks:
            continue
        delete_document_chunks(doc.id)
        texts = [c.content for c in chunks]
        embeddings = embed_texts(texts)
        if embeddings is None:
            continue
        chunk_ids = [f"doc_{doc.id}_chunk_{c.id}" for c in chunks]
        metadatas = [
            {
                "document_id": doc.id,
                "chunk_id": c.id,
                "section_title": c.section_title or "",
                "chunk_type": c.chunk_type or "text",
                "page_start": c.page_start or 0,
            }
            for c in chunks
        ]
        add_chunks(chunk_ids, texts, embeddings, metadatas)
        for i, chunk in enumerate(chunks):
            chunk.chroma_id = chunk_ids[i]
        total_chunks += len(chunks)

    db.commit()
    return {"code": 0, "msg": f"全量重建完成，共 {total_chunks} 个向量", "data": {"total_chunks": total_chunks}}


@router.get("/bm25-status", summary="BM25索引诊断")
def get_bm25_status(
    current_user: User = Depends(get_current_user),
):
    """诊断接口：查看BM25索引状态"""
    from app.services.search_service import get_bm25_index
    idx = get_bm25_index()
    doc_ids = set()
    for meta in idx.doc_metas:
        doc_ids.add(meta.get("document_id"))
    return {
        "code": 0,
        "data": {
            "total_docs_in_index": idx.N,
            "unique_document_ids": list(doc_ids),
            "avg_doc_len": idx.avg_doc_len,
            "has_metadata": len(idx.doc_metas) > 0,
            "sample_meta": idx.doc_metas[0] if idx.doc_metas else {},
            "sample_text": idx.documents[0][:200] if idx.documents else "",
        },
    }


@router.get("/stats", summary="知识库详细统计")
def get_detailed_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库的详细统计数据（与 overview 互补）"""
    vector_stats = get_collection_stats()

    # 按文档类型统计
    type_stats = db.query(
        Document.doc_type,
        func.count(Document.id)
    ).filter(Document.is_deleted == 0).group_by(Document.doc_type).all()

    return {
        "code": 0,
        "data": {
            "vector_stats": vector_stats,
            "type_distribution": [{"type": t or "unknown", "count": c} for t, c in type_stats],
        },
    }
