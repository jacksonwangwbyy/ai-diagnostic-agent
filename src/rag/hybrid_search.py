"""
混合检索 — BM25 关键词检索 + 向量语义检索 + RRF 融合 + CrossEncoder 重排序

流程：
1. 查询改写（可选）：LLM 将口语化描述转为结构化查询
2. 并行执行向量检索和 BM25 关键词检索
3. RRF (Reciprocal Rank Fusion) 融合两路结果
4. CrossEncoder 重排序，返回 top_k
"""
import re
import logging
import threading
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

from src.rag.vectorstore import search_with_scores
from src.rag.reranker import rerank

logger = logging.getLogger(__name__)

_bm25_index = None
_bm25_lock = threading.Lock()


def _tokenize(text: str) -> list[str]:
    """中文分词（字符级 + 2-gram，兼容英文单词）"""
    tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', text.lower())
    result = []
    for token in tokens:
        if re.match(r'[\u4e00-\u9fff]', token):
            for i in range(len(token)):
                result.append(token[i])
                if i + 1 < len(token):
                    result.append(token[i:i+2])
        else:
            result.append(token)
    return result


class BM25Index:
    """BM25 关键词检索索引"""

    def __init__(self, documents: list[Document]):
        self.documents = documents
        if documents:
            from rank_bm25 import BM25Okapi
            tokenized = [_tokenize(doc.page_content) for doc in documents]
            self.bm25 = BM25Okapi(tokenized)
        else:
            self.bm25 = None

    def search(self, query: str, k: int = 20) -> list[Document]:
        """BM25 关键词检索"""
        if not self.bm25 or not self.documents:
            return []

        tokenized_query = _tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        scored_docs = list(zip(self.documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        return [doc for doc, score in scored_docs[:k] if score > 0]


def _get_bm25_index() -> BM25Index | None:
    """获取 BM25 索引（懒加载，从向量库加载文档构建）"""
    global _bm25_index
    if _bm25_index is None:
        with _bm25_lock:
            if _bm25_index is None:
                try:
                    from src.rag.vectorstore import search
                    all_docs = search("", k=1000)
                    _bm25_index = BM25Index(all_docs)
                    logger.info(f"BM25 索引构建完成，共 {len(all_docs)} 个文档")
                except Exception as e:
                    logger.warning(f"BM25 索引构建失败: {e}")
                    _bm25_index = BM25Index([])
    return _bm25_index


def rrf_fuse(
    ranked_lists: list[list[Document]],
    k: int = 60,
    top_k: int = 20,
) -> list[Document]:
    """
    Reciprocal Rank Fusion — 融合多个排序列表

    score(doc) = sum(1 / (k + rank_i)) for each list i
    """
    doc_scores: dict[str, tuple[Document, float]] = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list, 1):
            # 使用内容哈希去重，避免 id() 导致相同内容的不同对象无法合并
            doc_key = hash((doc.page_content, doc.metadata.get("filename", "")))
            if doc_key in doc_scores:
                existing_doc, existing_score = doc_scores[doc_key]
                doc_scores[doc_key] = (existing_doc, existing_score + 1.0 / (k + rank))
            else:
                doc_scores[doc_key] = (doc, 1.0 / (k + rank))

    sorted_docs = sorted(doc_scores.values(), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in sorted_docs[:top_k]]


REWRITE_PROMPT = """你是一个搜索查询优化器。将用户的口语化描述改写为适合技术文档检索的结构化查询。

规则：
- 提取关键技术术语
- 添加相关同义词
- 保持简洁（10-20 个字）
- 只输出改写后的查询，不要解释

用户描述：{question}
改写查询："""


def rewrite_query(question: str, llm=None) -> str:
    """
    查询改写：将口语化描述转为结构化检索查询

    Args:
        question: 用户原始问题
        llm: LLM 实例（None 则跳过改写）

    Returns:
        改写后的查询（失败则返回原始查询）
    """
    if llm is None:
        return question

    try:
        from src.llm.client import extract_text
        response = llm.invoke([
            HumanMessage(content=REWRITE_PROMPT.format(question=question))
        ])
        rewritten = extract_text(response.content).strip()
        if rewritten:
            logger.info(f"查询改写: '{question}' → '{rewritten}'")
            return rewritten
    except Exception as e:
        logger.warning(f"查询改写失败: {e}")

    return question


def enhanced_search(
    query: str,
    k: int = 5,
    use_rewrite: bool = False,
    llm=None,
) -> list[tuple[Document, float]]:
    """
    增强检索入口 — 混合检索 + 重排序

    流程: 查询改写(可选) → 向量+BM25并行检索 → RRF融合 → CrossEncoder重排

    Args:
        query: 用户查询
        k: 最终返回结果数
        use_rewrite: 是否启用查询改写
        llm: 查询改写用的 LLM

    Returns:
        [(Document, score), ...] 按相关性排序
    """
    search_query = query
    if use_rewrite and llm:
        search_query = rewrite_query(query, llm)

    # 1. 向量语义检索 (top 20)
    vector_results = search_with_scores(search_query, k=20)
    vector_docs = [doc for doc, _ in vector_results]

    # 2. BM25 关键词检索 (top 20)
    bm25_index = _get_bm25_index()
    bm25_docs = bm25_index.search(search_query, k=20) if bm25_index else []

    # 3. RRF 融合
    if bm25_docs:
        fused_docs = rrf_fuse([vector_docs, bm25_docs], k=60, top_k=20)
    else:
        fused_docs = vector_docs

    # 4. CrossEncoder 重排序
    if fused_docs:
        reranked = rerank(search_query, fused_docs, top_k=k)
    else:
        reranked = []

    return reranked
