"""
ChromaDB 向量存储服务（M2 模块）
封装 ChromaDB 的 collection 管理、文档增删、向量检索
"""
import logging
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# ChromaDB 持久化存储路径
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_data")

# 全局 ChromaDB 客户端（懒初始化）
_chroma_client = None
_collection_name = "financial_reports"


def _get_client() -> chromadb.Client:
    """获取或创建 ChromaDB 持久化客户端"""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB 客户端初始化完成，存储路径: {CHROMA_PERSIST_DIR}")
    return _chroma_client


def get_collection():
    """获取财报知识库的向量 collection"""
    client = _get_client()
    return client.get_or_create_collection(
        name=_collection_name,
        metadata={"hnsw:space": "cosine"},  # 使用余弦相似度
    )


def add_chunks(
    chunk_ids: List[str],
    texts: List[str],
    embeddings: List[List[float]],
    metadatas: List[dict],
):
    """
    批量添加文档 chunk 到向量库
    :param chunk_ids: chunk 唯一 ID 列表，如 ["doc_1_chunk_3"]
    :param texts: chunk 文本内容列表
    :param embeddings: 对应的向量嵌入列表
    :param metadatas: 元数据列表，如 [{"document_id": 1, "section": "利润表", "page": 5}]
    """
    if not chunk_ids:
        return
    collection = get_collection()
    collection.add(
        ids=chunk_ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info(f"已向 ChromaDB 添加 {len(chunk_ids)} 个向量")


def search_similar(
    query_embedding: List[float],
    top_k: int = 20,
    filter_doc_ids: Optional[List[int]] = None,
) -> List[dict]:
    """
    向量相似度检索
    :param query_embedding: 查询向量
    :param top_k: 返回数量
    :param filter_doc_ids: 限定在指定文档 ID 范围内检索（可选）
    :return: [{id, text, metadata, distance}, ...]
    """
    collection = get_collection()
    where_filter = None
    if filter_doc_ids:
        # ChromaDB 的 where 过滤
        where_filter = {"document_id": {"$in": filter_doc_ids}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # 展平结果
    items = []
    if results["ids"] and results["ids"][0]:
        for i, chunk_id in enumerate(results["ids"][0]):
            items.append({
                "id": chunk_id,
                "text": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 1.0,
            })
    return items


def delete_document_chunks(document_id: int):
    """删除指定文档的所有 chunk 向量"""
    collection = get_collection()
    try:
        collection.delete(where={"document_id": document_id})
        logger.info(f"已从 ChromaDB 删除文档 {document_id} 的向量")
    except Exception as e:
        logger.warning(f"删除文档向量失败: {e}")


def get_collection_stats() -> dict:
    """获取向量库统计信息"""
    try:
        collection = get_collection()
        count = collection.count()
        return {"total_vectors": count, "collection_name": _collection_name}
    except Exception:
        return {"total_vectors": 0, "collection_name": _collection_name}
