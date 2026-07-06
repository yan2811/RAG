"""
混合检索服务（M2 模块）—— 改进版
向量检索 + BM25 关键词检索（带文档过滤）→ RRF 融合 → Top-K
"""
import logging
from typing import List, Optional
from app.services.embedding_service import embed_query, BM25Index
from app.services.vector_store import search_similar

logger = logging.getLogger(__name__)

_bm25_index: Optional[BM25Index] = None
_bm25_metadata: dict = {}


def get_bm25_index() -> BM25Index:
    global _bm25_index
    if _bm25_index is None:
        _bm25_index = BM25Index()
    return _bm25_index


def add_to_bm25(chunk_id: str, text: str, metadata: dict):
    """向 BM25 索引添加文档"""
    idx = get_bm25_index()
    idx.add_document(chunk_id, text, metadata)
    _bm25_metadata[chunk_id] = metadata


def build_bm25():
    get_bm25_index().build()


def rebuild_bm25_from_db(db_session):
    """从数据库所有已解析文档的 chunks 重建 BM25 索引"""
    from app.models.document import Document, Chunk
    idx = get_bm25_index()
    # 清空
    idx.documents.clear()
    idx.tokenized_docs.clear()
    idx.doc_metas.clear()
    idx.doc_freq.clear()
    idx.N = 0
    _bm25_metadata.clear()

    docs = db_session.query(Document).filter(
        Document.is_deleted == 0, Document.parse_status == "completed"
    ).all()

    total = 0
    for doc in docs:
        chunks = db_session.query(Chunk).filter(Chunk.document_id == doc.id).all()
        for c in chunks:
            chunk_id = f"doc_{doc.id}_chunk_{c.id}"
            meta = {
                "document_id": doc.id,
                "file_name": doc.file_name,
                "section_title": c.section_title or "",
                "chunk_type": c.chunk_type or "text",
                "page_start": c.page_start or 0,
                "company_code": doc.company_code or "",
                "fiscal_year": doc.fiscal_year or 0,
            }
            add_to_bm25(chunk_id, c.content, meta)
            total += 1

    build_bm25()
    logger.info(f"BM25 索引重建完成：{total} 个分块，来自 {len(docs)} 个文档")
    return total


def hybrid_search(
    query: str,
    top_k: int = 10,
    filter_doc_ids: Optional[List[int]] = None,
    vector_weight: float = 0.6,
) -> List[dict]:
    """
    混合检索：向量 + BM25 → RRF 融合
    支持按文档 ID 过滤（仅对 BM25 生效，ChromaDB 自带 where 过滤）
    """
    results = []

    # Step 1: 向量检索
    query_emb = embed_query(query)
    if query_emb:
        vector_results = search_similar(query_emb, top_k=20, filter_doc_ids=filter_doc_ids)
        for r in vector_results:
            r["source"] = "vector"
            r["score"] = 1.0 - r.get("distance", 0)
        results.extend(vector_results)
    else:
        logger.info("Embedding 模型不可用，跳过向量检索")

    # Step 2: BM25 关键词检索（带文档过滤）
    bm25 = get_bm25_index()
    # 如果索引为空，尝试自动重建（兜底机制）
    if bm25.N == 0:
        try:
            from app.core.database import SessionLocal
            db = SessionLocal()
            rebuild_bm25_from_db(db)
            db.close()
            logger.info("BM25 索引为空，已自动重建")
        except Exception as e:
            logger.warning(f"BM25 自动重建失败: {e}")
    if bm25.N > 0:
        bm25_results = bm25.search(query, top_k=20)
        for idx, score in bm25_results:
            # 获取该文档的 metadata
            meta = bm25.doc_metas[idx] if idx < len(bm25.doc_metas) else {}
            doc_id = meta.get("document_id")

            # 文档过滤
            if filter_doc_ids and doc_id not in filter_doc_ids:
                continue

            chunk_id = f"doc_{doc_id}_chunk_{idx}"
            results.append({
                "id": chunk_id,
                "text": bm25.documents[idx] if idx < len(bm25.documents) else "",
                "metadata": meta,
                "score": score,
                "source": "bm25",
            })

    if not results:
        # 无结果时直接使用 AI 直接回答
        return []

    # Step 3: RRF 融合
    fused = {}
    for r in results:
        cid = r["id"]
        w = vector_weight if r["source"] == "vector" else (1 - vector_weight)
        if cid not in fused:
            fused[cid] = {"id": cid, "text": r["text"], "metadata": r["metadata"], "score": 0}
        fused[cid]["score"] += r["score"] * w

    sorted_results = sorted(fused.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results[:top_k]
