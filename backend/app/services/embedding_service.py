"""
向量嵌入与关键词索引服务（M2 模块）
- BGE 模型文本向量化（懒加载，首次使用时加载）
- jieba 分词 + BM25 关键词索引
"""
import os
import logging
import jieba
import numpy as np
from typing import List, Optional
from collections import defaultdict
import math

# 离线模式：BGE 模型体积大（2GB），环境受限时优先使用 BM25
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

logger = logging.getLogger(__name__)

# 全局懒加载的 embedding 模型实例
_embedding_model = None


def _get_embedding_model():
    """
    懒加载 BGE 中文 Embedding 模型
    首次调用时从 HuggingFace 下载，后续调用复用缓存
    设置短超时避免 HuggingFace 不可达时长时间阻塞
    """
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("正在加载 BGE-large-zh-v1.5 模型...")
            _embedding_model = SentenceTransformer(
                "BAAI/bge-large-zh-v1.5",
                trust_remote_code=False,
            )
            logger.info("BGE 模型加载完成")
        except ImportError:
            logger.warning(
                "sentence-transformers 未安装，向量检索不可用。"
                "请运行: pip install sentence-transformers"
            )
            return None
        except OSError as e:
            logger.warning(f"BGE 模型加载失败(网络不可达): {e}")
            return None
        except Exception as e:
            logger.warning(f"BGE 模型加载失败: {e}")
            return None
    return _embedding_model


def embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """
    将文本列表转为向量嵌入
    :param texts: 文本列表，每个元素是一个 chunk 的内容
    :return: 向量列表，每个向量是 1024 维浮点数列表；模型未就绪返回 None
    """
    model = _get_embedding_model()
    if model is None:
        return None
    # BGE 模型建议对文本添加 instruction 前缀以提升效果
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,  # 归一化，便于余弦相似度计算
        show_progress_bar=False,
    )
    return embeddings.tolist()


def embed_query(query: str) -> Optional[List[float]]:
    """
    将查询文本转为向量嵌入
    BGE 模型对查询建议加前缀 "为这个句子生成表示以用于检索相关文章："
    """
    model = _get_embedding_model()
    if model is None:
        return None
    # BGE 推荐的查询前缀
    query_with_prefix = f"为这个句子生成表示以用于检索相关文章：{query}"
    embedding = model.encode(
        [query_with_prefix],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embedding[0].tolist()


# ============================================================
# BM25 关键词检索
# ============================================================

class BM25Index:
    """
    简易 BM25 关键词检索索引
    用于与向量检索互补的精确关键词匹配
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1  # 词频饱和度参数
        self.b = b    # 文档长度归一化参数
        self.documents: List[str] = []
        self.tokenized_docs: List[List[str]] = []  # jieba 分词后的词列表
        self.doc_ids: List[str] = []
        self.doc_metas: List[dict] = []
        self.doc_freq: dict = defaultdict(int)
        self.avg_doc_len: float = 0
        self.N: int = 0  # 文档总数

    def add_document(self, doc_id: str, text: str, metadata: dict = None):
        """向索引中添加一个文档"""
        tokens = list(jieba.cut(text.lower()))
        tokens = [t.strip() for t in tokens if len(t.strip()) > 1]
        self.documents.append(text)
        self.tokenized_docs.append(tokens)
        self.doc_ids.append(doc_id)
        self.doc_metas.append(metadata or {})
        self.N += 1
        unique_tokens = set(tokens)
        for token in unique_tokens: # 统计文档频率
            self.doc_freq[token] += 1

    def build(self):
        """构建索引（计算平均文档长度）"""
        if self.N > 0:
            total_len = sum(len(doc) for doc in self.tokenized_docs)
            self.avg_doc_len = total_len / self.N
        logger.info(f"BM25 索引构建完成，共 {self.N} 篇文档")

    def search(self, query: str, top_k: int = 20) -> List[tuple]:
        """
        搜索并返回 Top-K 结果
        :param query: 查询文本
        :param top_k: 返回数量
        :return: [(doc_index, score), ...] 按分数降序排列
        """
        if self.N == 0:
            return []

        query_tokens = list(jieba.cut(query.lower()))
        query_tokens = [t.strip() for t in query_tokens if len(t.strip()) > 1]

        scores = []
        for idx, doc_tokens in enumerate(self.tokenized_docs):
            doc_len = len(doc_tokens)
            score = 0.0
            # 计算每个查询词的 BM25 得分
            tf = defaultdict(int)
            for t in doc_tokens:
                tf[t] += 1

            for token in query_tokens:
                if token not in self.doc_freq:
                    continue
                df = self.doc_freq[token]
                idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)
                # BM25 公式
                numerator = tf[token] * (self.k1 + 1)
                denominator = tf[token] + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
                score += idf * numerator / denominator

            if score > 0:
                scores.append((idx, score))

        # 按分数降序排列
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
