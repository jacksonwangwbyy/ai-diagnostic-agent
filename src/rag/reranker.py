"""
CrossEncoder 重排序 — 对初次检索结果进行精排

使用 cross-encoder/ms-marco-MiniLM-L-6-v2 模型，
对 (query, document) 对计算相关性分数，按分数降序返回 top_k 结果。
"""
import logging
import threading
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_reranker = None
_reranker_lock = threading.Lock()

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_reranker():
    """懒加载 CrossEncoder（线程安全单例）"""
    global _reranker
    if _reranker is None:
        with _reranker_lock:
            if _reranker is None:
                from sentence_transformers import CrossEncoder
                logger.info(f"加载 Reranker 模型: {RERANKER_MODEL}")
                _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def rerank(
    query: str,
    documents: list[Document],
    top_k: int = 5,
) -> list[Document]:
    """
    对文档列表按与 query 的相关性重排序

    Args:
        query: 用户查询
        documents: 待排序的文档列表
        top_k: 返回前 k 个最相关的文档

    Returns:
        按相关性降序排列的文档列表
    """
    if not documents:
        return []

    model = _get_reranker()
    pairs = [[query, doc.page_content] for doc in documents]
    scores = model.predict(pairs)

    scored_docs = list(zip(documents, scores))
    scored_docs.sort(key=lambda x: x[1], reverse=True)

    return [doc for doc, _ in scored_docs[:top_k]]
