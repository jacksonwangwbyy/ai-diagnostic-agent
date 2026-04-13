# 迭代 2：RAG 优化 & 评估 + 新诊断工具 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提升 RAG 检索质量（Reranking + 混合检索 + 查询改写），建立自动评估体系，新增 2 个诊断工具，同步文档。

**Architecture:** 在现有向量检索管道中插入 BM25 混合检索和 CrossEncoder 重排序。新增评估框架验证优化效果。添加设备重启和固件检查工具扩展 Agent 能力。每个子任务完成后进行代码审查。

**Tech Stack:** Python 3.11, sentence-transformers (CrossEncoder), rank-bm25, pytest, LangChain

---

## 文件结构

### 新建文件
- `src/rag/reranker.py` — CrossEncoder 重排序
- `src/rag/hybrid_search.py` — BM25 索引 + RRF 融合 + 查询改写 + enhanced_search 入口
- `src/tools/device_restart.py` — 设备/服务重启工具
- `src/tools/firmware_check.py` — 固件版本检查工具
- `evaluation/eval_dataset.json` — 评估数据集
- `evaluation/run_eval.py` — 自动评估脚本
- `evaluation/README.md` — 评估使用说明
- `tests/test_reranker.py` — Reranker 测试
- `tests/test_hybrid_search.py` — 混合检索测试
- `tests/test_device_restart.py` — 设备重启工具测试
- `tests/test_firmware_check.py` — 固件检查工具测试

### 修改文件
- `requirements.txt` — 添加 rank-bm25
- `src/rag/chain.py` — rag_query/rag_stream 使用 enhanced_search
- `src/tools/knowledge_search.py` — 使用 enhanced_search
- `src/agent/diagnostic_agent.py` — 注册 2 个新工具
- `README.md` — 更新功能列表和已完成项
- `docs/usage-and-learning-guide.md` — 添加 RAG 优化章节

---

## Task 1: 添加 rank-bm25 依赖

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 添加依赖**

在 `requirements.txt` 末尾添加：

```
rank-bm25>=0.2,<0.3
```

- [ ] **Step 2: 安装依赖**

Run: `pip install rank-bm25>=0.2,<0.3`
Expected: Successfully installed

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add rank-bm25 for hybrid search"
```

---

## Task 2: 实现 CrossEncoder Reranker

**Files:**
- Create: `src/rag/reranker.py`
- Create: `tests/test_reranker.py`

- [ ] **Step 1: 编写 reranker 测试**

创建 `tests/test_reranker.py`：

```python
"""测试：CrossEncoder 重排序"""
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


class TestRerank:

    def test_rerank_reorders_by_score(self):
        """重排序按分数降序排列"""
        from src.rag.reranker import rerank

        docs = [
            Document(page_content="不太相关的内容", metadata={"filename": "a.md"}),
            Document(page_content="非常相关的制冰机故障", metadata={"filename": "b.md"}),
            Document(page_content="完全无关", metadata={"filename": "c.md"}),
        ]

        # Mock CrossEncoder 返回分数：第二个文档最相关
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.2, 0.9, 0.1]

        with patch("src.rag.reranker._get_reranker", return_value=mock_model):
            result = rerank("制冰机故障", docs, top_k=2)
            assert len(result) == 2
            assert result[0].metadata["filename"] == "b.md"
            assert result[1].metadata["filename"] == "a.md"

    def test_rerank_top_k_limit(self):
        """top_k 限制返回数量"""
        from src.rag.reranker import rerank

        docs = [Document(page_content=f"doc {i}", metadata={}) for i in range(10)]
        mock_model = MagicMock()
        mock_model.predict.return_value = list(range(10))

        with patch("src.rag.reranker._get_reranker", return_value=mock_model):
            result = rerank("query", docs, top_k=3)
            assert len(result) == 3

    def test_rerank_empty_docs(self):
        """空文档列表"""
        from src.rag.reranker import rerank
        result = rerank("query", [], top_k=5)
        assert result == []

    def test_rerank_fewer_than_top_k(self):
        """文档数少于 top_k"""
        from src.rag.reranker import rerank

        docs = [Document(page_content="only one", metadata={})]
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5]

        with patch("src.rag.reranker._get_reranker", return_value=mock_model):
            result = rerank("query", docs, top_k=5)
            assert len(result) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reranker.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 实现 reranker**

创建 `src/rag/reranker.py`：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reranker.py -v`
Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/rag/reranker.py tests/test_reranker.py
git commit -m "feat: add CrossEncoder reranker for search result refinement"
```

---

## Task 3: 实现混合检索（BM25 + RRF + 查询改写）

**Files:**
- Create: `src/rag/hybrid_search.py`
- Create: `tests/test_hybrid_search.py`

- [ ] **Step 1: 编写混合检索测试**

创建 `tests/test_hybrid_search.py`：

```python
"""测试：混合检索（BM25 + RRF + 查询改写）"""
import jieba
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from src.rag.hybrid_search import (
    BM25Index,
    rrf_fuse,
    rewrite_query,
    enhanced_search,
)


class TestBM25Index:

    def test_build_and_search(self):
        """构建索引并搜索"""
        docs = [
            Document(page_content="制冰机压缩机温度过高导致停机", metadata={"filename": "a.md"}),
            Document(page_content="咖啡机水温不达标需要检查加热元件", metadata={"filename": "b.md"}),
            Document(page_content="机械臂归零失败请检查限位开关", metadata={"filename": "c.md"}),
        ]
        index = BM25Index(docs)
        results = index.search("制冰机温度", k=2)
        assert len(results) == 2
        assert results[0].metadata["filename"] == "a.md"

    def test_search_empty_index(self):
        """空索引搜索"""
        index = BM25Index([])
        results = index.search("任何查询", k=5)
        assert results == []

    def test_search_k_larger_than_docs(self):
        """k 大于文档数"""
        docs = [Document(page_content="唯一文档", metadata={})]
        index = BM25Index(docs)
        results = index.search("文档", k=10)
        assert len(results) == 1


class TestRRFFuse:

    def test_fuse_two_lists(self):
        """RRF 融合两个排序列表"""
        doc_a = Document(page_content="A", metadata={"id": "a"})
        doc_b = Document(page_content="B", metadata={"id": "b"})
        doc_c = Document(page_content="C", metadata={"id": "c"})

        list1 = [doc_a, doc_b, doc_c]  # a=rank1, b=rank2, c=rank3
        list2 = [doc_c, doc_a, doc_b]  # c=rank1, a=rank2, b=rank3

        fused = rrf_fuse([list1, list2], k=60, top_k=3)
        assert len(fused) == 3
        # doc_a: 1/(60+1) + 1/(60+2) = 0.01639 + 0.01613 = 0.03252
        # doc_c: 1/(60+3) + 1/(60+1) = 0.01587 + 0.01639 = 0.03226
        # doc_a 应该排在 doc_c 前面
        assert fused[0].page_content == "A"

    def test_fuse_empty_lists(self):
        """空列表融合"""
        result = rrf_fuse([[], []], k=60, top_k=5)
        assert result == []


class TestRewriteQuery:

    def test_rewrite_returns_string(self):
        """查询改写返回字符串"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="制冰机 出冰量不足 故障排查")

        result = rewrite_query("冰不够了", mock_llm)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_rewrite_fallback_on_error(self):
        """改写失败时返回原始查询"""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API error")

        result = rewrite_query("冰不够了", mock_llm)
        assert result == "冰不够了"


class TestEnhancedSearch:

    def test_enhanced_search_returns_results(self):
        """enhanced_search 返回 (Document, float) 列表"""
        mock_docs = [
            (Document(page_content="结果1", metadata={"filename": "a.md"}), 0.9),
        ]
        with patch("src.rag.hybrid_search._get_bm25_index") as mock_bm25:
            mock_bm25_instance = MagicMock()
            mock_bm25_instance.search.return_value = [mock_docs[0][0]]
            mock_bm25.return_value = mock_bm25_instance

            with patch("src.rag.vectorstore.search_with_scores", return_value=mock_docs):
                with patch("src.rag.hybrid_search.rerank", side_effect=lambda q, d, top_k: d[:top_k]):
                    results = enhanced_search("制冰机故障", k=5)
                    assert len(results) >= 1
                    assert isinstance(results[0], tuple)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_hybrid_search.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 实现混合检索**

创建 `src/rag/hybrid_search.py`：

```python
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
from langchain_core.messages import HumanMessage, SystemMessage

from src.rag.vectorstore import search_with_scores
from src.rag.reranker import rerank

logger = logging.getLogger(__name__)

_bm25_index = None
_bm25_lock = threading.Lock()


def _tokenize(text: str) -> list[str]:
    """中文分词（简单实现：按字符 + 按标点/空格切分）"""
    # 使用正则按非字母数字中文字符切分
    tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', text.lower())
    # 对中文进一步按字切分（简单但有效）
    result = []
    for token in tokens:
        if re.match(r'[\u4e00-\u9fff]', token):
            # 中文：按 2-gram 切分
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
                    # 用空查询获取所有文档（取足够多的）
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

    Args:
        ranked_lists: 多个已排序的文档列表
        k: RRF 参数（默认 60，业界标准）
        top_k: 返回前 k 个结果
    """
    doc_scores: dict[int, tuple[Document, float]] = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list, 1):
            doc_id = id(doc)
            if doc_id in doc_scores:
                existing_doc, existing_score = doc_scores[doc_id]
                doc_scores[doc_id] = (existing_doc, existing_score + 1.0 / (k + rank))
            else:
                doc_scores[doc_id] = (doc, 1.0 / (k + rank))

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
        llm: 查询改写用的 LLM（use_rewrite=True 时需要）

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

    # 返回 (doc, score) 格式（score 按排序位置递减）
    return [(doc, 1.0 - i * 0.1) for i, doc in enumerate(reranked)]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_hybrid_search.py -v`
Expected: 8 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/rag/hybrid_search.py tests/test_hybrid_search.py
git commit -m "feat: add hybrid search with BM25 + RRF fusion + query rewriting"
```

---

## Task 4: 集成增强检索到 RAG 链和知识库搜索

**Files:**
- Modify: `src/rag/chain.py`
- Modify: `src/tools/knowledge_search.py`

- [ ] **Step 1: 修改 chain.py 使用 enhanced_search**

在 `src/rag/chain.py` 中：

将 `rag_query` 函数中的：
```python
results = search_with_scores(question, k=k)
```
替换为：
```python
from src.rag.hybrid_search import enhanced_search
results = enhanced_search(question, k=k)
```

将 `rag_stream` 函数中的：
```python
results = search_with_scores(question, k=k)
```
替换为：
```python
results = enhanced_search(question, k=k)
```

同时在文件顶部的 import 中添加：
```python
from src.rag.hybrid_search import enhanced_search
```

可以保留原有的 `from src.rag.vectorstore import search_with_scores` import，因为 `format_context` 仍然需要处理 `(Document, float)` 元组。

- [ ] **Step 2: 修改 knowledge_search.py 使用 enhanced_search**

在 `src/tools/knowledge_search.py` 中：

将：
```python
from src.rag.vectorstore import search_with_scores
```
替换为：
```python
from src.rag.hybrid_search import enhanced_search
```

将 `search_knowledge_base` 函数中的：
```python
results = search_with_scores(query, k=5)
```
替换为：
```python
results = enhanced_search(query, k=5)
```

- [ ] **Step 3: 运行现有测试确认不破坏**

Run: `.venv/Scripts/python.exe -m pytest tests/test_knowledge_search.py -v`
Expected: 5 tests PASSED（因为 enhanced_search 在测试中被 mock 为 search_with_scores）

注意：如果测试因 import 路径变化而失败，需要更新测试中的 mock 路径：
将 `patch("src.tools.knowledge_search.search_with_scores", ...)` 改为 `patch("src.tools.knowledge_search.enhanced_search", ...)`

- [ ] **Step 4: Commit**

```bash
git add src/rag/chain.py src/tools/knowledge_search.py
git commit -m "feat: integrate enhanced search into RAG chain and knowledge search tool"
```

---

## Task 5: 新增设备重启工具

**Files:**
- Create: `src/tools/device_restart.py`
- Create: `tests/test_device_restart.py`

- [ ] **Step 1: 编写设备重启工具测试**

创建 `tests/test_device_restart.py`：

```python
"""测试：设备重启工具"""
from unittest.mock import patch, MagicMock
from src.tools.device_restart import restart_device_service


class TestRestartDeviceService:

    def test_restart_middleware(self):
        """重启中间件服务"""
        mock_result = MagicMock(stdout="restarted", stderr="", returncode=0)
        with patch("src.tools.device_restart.subprocess.run", return_value=mock_result):
            result = restart_device_service.invoke({"service": "middleware"})
            assert "成功" in result or "已重启" in result

    def test_restart_deploy_client(self):
        """重启部署客户端"""
        mock_result = MagicMock(stdout="restarted", stderr="", returncode=0)
        with patch("src.tools.device_restart.subprocess.run", return_value=mock_result):
            result = restart_device_service.invoke({"service": "deploy"})
            assert "成功" in result or "已重启" in result

    def test_unsupported_service(self):
        """不支持的服务名"""
        result = restart_device_service.invoke({"service": "rm -rf /"})
        assert "不支持" in result

    def test_ssh_failure(self):
        """SSH 执行失败"""
        mock_result = MagicMock(stdout="", stderr="Connection refused", returncode=1)
        with patch("src.tools.device_restart.subprocess.run", return_value=mock_result):
            result = restart_device_service.invoke({"service": "middleware"})
            assert "失败" in result or "无法" in result

    def test_ssh_timeout(self):
        """SSH 超时"""
        import subprocess
        with patch("src.tools.device_restart.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=15)):
            result = restart_device_service.invoke({"service": "middleware"})
            assert "超时" in result
```

- [ ] **Step 2: 实现设备重启工具**

创建 `src/tools/device_restart.py`：

```python
"""
工具：设备服务重启

通过 SSH 远程重启指定的设备服务。
安全设计：只允许重启白名单中的服务，不允许执行任意命令。
"""
import subprocess
from langchain_core.tools import tool
from src.config.settings import settings

# 服务重启命令白名单
SERVICE_COMMANDS = {
    "middleware": "systemctl restart bar_middleware",
    "deploy": "systemctl restart bar-deploy-client",
    "docker": "docker restart $(docker ps -q | head -1)",
    "system": "sudo reboot",
}


@tool
def restart_device_service(service: str = "middleware") -> str:
    """重启饮吧设备上的指定服务。
    当故障排查后需要重启服务来恢复设备正常运行时使用此工具。

    Args:
        service: 要重启的服务名。可选值:
            - "middleware": 重启 bar_middleware 中间件服务（默认）
            - "deploy": 重启 bar-deploy-client 部署客户端
            - "docker": 重启 Docker 主容器
            - "system": 整机重启（谨慎使用）
    """
    if service not in SERVICE_COMMANDS:
        available = ", ".join(SERVICE_COMMANDS.keys())
        return f"不支持的服务: {service}。可选: {available}"

    command = SERVICE_COMMANDS[service]

    ssh_cmd = [
        "ssh",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        f"{settings.DEVICE_SSH_USER}@{settings.DEVICE_SSH_HOST}",
        command,
    ]

    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return f"✅ 服务 [{service}] 已重启成功。\n输出: {result.stdout.strip() or '(无输出)'}"
        else:
            error = result.stderr.strip()
            return f"❌ 重启 [{service}] 失败: {error}"

    except subprocess.TimeoutExpired:
        return f"⏰ 重启 [{service}] 超时，设备可能正在重启中，请稍后检查设备状态。"
    except FileNotFoundError:
        return "SSH 客户端未找到，请确认系统已安装 SSH。"
```

- [ ] **Step 3: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_device_restart.py -v`
Expected: 5 tests PASSED

- [ ] **Step 4: Commit**

```bash
git add src/tools/device_restart.py tests/test_device_restart.py
git commit -m "feat: add device service restart tool with SSH command whitelist"
```

---

## Task 6: 新增固件版本检查工具

**Files:**
- Create: `src/tools/firmware_check.py`
- Create: `tests/test_firmware_check.py`

- [ ] **Step 1: 编写固件检查工具测试**

创建 `tests/test_firmware_check.py`：

```python
"""测试：固件版本检查工具"""
from unittest.mock import patch, MagicMock
from src.tools.firmware_check import check_firmware_version


class TestCheckFirmwareVersion:

    def test_version_check_success(self):
        """成功查询版本"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"version": "2.1.0"}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.tools.firmware_check.httpx.get", return_value=mock_resp):
            result = check_firmware_version.invoke({})
            assert "2.1.0" in result

    def test_version_with_deploy_info(self):
        """查询版本和部署信息"""
        version_resp = MagicMock()
        version_resp.json.return_value = {"version": "2.1.0"}
        version_resp.raise_for_status = MagicMock()

        with patch("src.tools.firmware_check.httpx.get", return_value=version_resp):
            result = check_firmware_version.invoke({})
            assert "2.1.0" in result

    def test_middleware_offline(self):
        """中间件不可达"""
        with patch("src.tools.firmware_check.httpx.get", side_effect=Exception("Connection refused")):
            result = check_firmware_version.invoke({})
            assert "无法连接" in result or "离线" in result

    def test_check_specific_component(self):
        """查询指定组件版本"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"version": "1.5.3"}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.tools.firmware_check.httpx.get", return_value=mock_resp):
            result = check_firmware_version.invoke({"component": "middleware"})
            assert "1.5.3" in result
```

- [ ] **Step 2: 实现固件检查工具**

创建 `src/tools/firmware_check.py`：

```python
"""
工具：固件/软件版本检查

查询设备各组件的软件版本，帮助诊断是否因版本过旧导致故障。
"""
import httpx
from langchain_core.tools import tool
from src.config.settings import settings

HTTP_TIMEOUT = 5.0

# 版本查询端点
VERSION_ENDPOINTS = {
    "middleware": "/mid/version",
    "deploy": "/deploy/version",
}


def _fetch_version(path: str) -> dict | None:
    """请求版本信息"""
    url = f"{settings.MIDDLEWARE_BASE_URL}{path}"
    try:
        resp = httpx.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


@tool
def check_firmware_version(component: str = "all") -> str:
    """查询饮吧设备的软件/固件版本信息。
    在排查因版本不兼容或版本过旧导致的故障时使用此工具。

    Args:
        component: 要查询的组件。可选值:
            - "all": 查询所有组件版本（默认）
            - "middleware": 只查询 bar_middleware 版本
            - "deploy": 只查询 bar-deploy-client 版本
    """
    if component != "all" and component not in VERSION_ENDPOINTS:
        available = ", ".join(["all"] + list(VERSION_ENDPOINTS.keys()))
        return f"不支持的组件: {component}。可选: {available}"

    if component != "all":
        path = VERSION_ENDPOINTS[component]
        data = _fetch_version(path)
        if data is None:
            return f"❌ 无法连接到 {component}，服务可能离线。"
        version = data.get("version", "未知")
        return f"📦 {component} 版本: {version}"

    # 查询所有组件
    lines = ["=== 设备软件版本信息 ===", ""]

    for name, path in VERSION_ENDPOINTS.items():
        data = _fetch_version(path)
        if data is None:
            lines.append(f"  {name}: ⚠️ 无法获取（服务可能离线）")
        else:
            version = data.get("version", "未知")
            lines.append(f"  {name}: {version}")

    return "\n".join(lines)
```

- [ ] **Step 3: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_firmware_check.py -v`
Expected: 4 tests PASSED

- [ ] **Step 4: Commit**

```bash
git add src/tools/firmware_check.py tests/test_firmware_check.py
git commit -m "feat: add firmware version check tool"
```

---

## Task 7: 注册新工具到 Agent

**Files:**
- Modify: `src/agent/diagnostic_agent.py`

- [ ] **Step 1: 添加新工具导入和注册**

在 `src/agent/diagnostic_agent.py` 中：

在现有 import 后添加：
```python
from src.tools.device_restart import restart_device_service
from src.tools.firmware_check import check_firmware_version
```

将 TOOLS 列表改为：
```python
TOOLS = [
    search_knowledge_base,
    fetch_device_logs,
    query_device_status,
    generate_diagnosis_report,
    restart_device_service,
    check_firmware_version,
]
```

在 AGENT_SYSTEM_PROMPT 的"你的能力"部分添加：
```
5. 重启设备服务（restart_device_service）
6. 检查固件/软件版本（check_firmware_version）
```

- [ ] **Step 2: 验证 Agent 能加载**

Run: `.venv/Scripts/python.exe -c "from src.agent.diagnostic_agent import TOOLS; print(f'Agent tools: {len(TOOLS)}')"`
Expected: `Agent tools: 6`

- [ ] **Step 3: Commit**

```bash
git add src/agent/diagnostic_agent.py
git commit -m "feat: register restart and firmware check tools in diagnostic agent"
```

---

## Task 8: 构建评估体系

**Files:**
- Create: `evaluation/eval_dataset.json`
- Create: `evaluation/run_eval.py`
- Create: `evaluation/README.md`

- [ ] **Step 1: 创建评估数据集**

创建 `evaluation/eval_dataset.json`，包含 20 组 Q&A 对：

```json
[
  {
    "question": "中间件启动不了怎么办？",
    "expected_answer_keywords": ["端口", "8003", "占用", "systemctl", "restart"],
    "expected_sources": ["middleware-faults.md", "bar_middleware_README.md"]
  },
  {
    "question": "制冰机不出冰是什么原因？",
    "expected_answer_keywords": ["压缩机", "温度", "过热", "保护"],
    "expected_sources": ["hardware-module-faults.md"]
  },
  {
    "question": "机械臂归零失败",
    "expected_answer_keywords": ["限位", "开关", "归零", "校准"],
    "expected_sources": ["robot-arm-faults.md"]
  },
  {
    "question": "OTA升级失败了",
    "expected_answer_keywords": ["下载", "网络", "重试", "版本"],
    "expected_sources": ["network-deploy-faults.md"]
  },
  {
    "question": "物料余量显示不对",
    "expected_answer_keywords": ["传感器", "漂移", "校准", "通道"],
    "expected_sources": ["material-monitor-faults.md"]
  },
  {
    "question": "Docker容器一直重启",
    "expected_answer_keywords": ["CrashLoop", "日志", "docker", "logs"],
    "expected_sources": ["network-deploy-faults.md"]
  },
  {
    "question": "咖啡机水温不够热",
    "expected_answer_keywords": ["加热", "元件", "温度", "传感器"],
    "expected_sources": ["hardware-module-faults.md"]
  },
  {
    "question": "设备日志规范是什么？",
    "expected_answer_keywords": ["日志", "格式", "级别", "Logback"],
    "expected_sources": ["设备端日志统一规范 v1.md"]
  },
  {
    "question": "杯子机卡杯了怎么处理？",
    "expected_answer_keywords": ["卡杯", "传感器", "清除", "杯道"],
    "expected_sources": ["hardware-module-faults.md"]
  },
  {
    "question": "中间件内存泄漏",
    "expected_answer_keywords": ["内存", "OOM", "重启", "监控"],
    "expected_sources": ["middleware-faults.md"]
  },
  {
    "question": "手爪抓取物体掉了",
    "expected_answer_keywords": ["手爪", "检测", "抓取", "传感器"],
    "expected_sources": ["robot-arm-faults.md", "机械臂手爪物体检测接口总结.md"]
  },
  {
    "question": "版本同步不一致怎么办？",
    "expected_answer_keywords": ["版本", "同步", "配置", "一致"],
    "expected_sources": ["版本同步逻辑说明.md", "network-deploy-faults.md"]
  },
  {
    "question": "视频内容下发失败",
    "expected_answer_keywords": ["视频", "下发", "网络", "存储"],
    "expected_sources": ["视频内容下发和删除逻辑说明.md", "network-deploy-faults.md"]
  },
  {
    "question": "逻辑锁是什么意思？",
    "expected_answer_keywords": ["锁", "状态", "互斥", "安全"],
    "expected_sources": ["逻辑锁.md"]
  },
  {
    "question": "冷凝器温度过高",
    "expected_answer_keywords": ["冷凝器", "温度", "散热", "清洁"],
    "expected_sources": ["hardware-module-faults.md"]
  },
  {
    "question": "物料通道堵了",
    "expected_answer_keywords": ["通道", "堵塞", "清理", "传感器"],
    "expected_sources": ["material-monitor-faults.md"]
  },
  {
    "question": "测试报告怎么写？",
    "expected_answer_keywords": ["测试", "报告", "规范", "格式"],
    "expected_sources": ["测试报告规范-v1.md"]
  },
  {
    "question": "扣盖机对不准",
    "expected_answer_keywords": ["扣盖", "对位", "校准", "传感器"],
    "expected_sources": ["hardware-module-faults.md"]
  },
  {
    "question": "中间件和硬件通信断开",
    "expected_answer_keywords": ["通信", "串口", "断开", "重连"],
    "expected_sources": ["middleware-faults.md"]
  },
  {
    "question": "执行状态机怎么工作的？",
    "expected_answer_keywords": ["状态机", "状态", "转换", "执行"],
    "expected_sources": ["执行状态机说明.md"]
  }
]
```

- [ ] **Step 2: 创建评估脚本**

创建 `evaluation/run_eval.py`：

```python
"""
RAG 评估脚本

用法：
    python evaluation/run_eval.py                    # 仅检索评估（不需要 LLM）
    python evaluation/run_eval.py --with-generation  # 检索 + 生成评估（需要 LLM）
"""
import json
import sys
from pathlib import Path

# 项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))


def evaluate_retrieval(dataset: list[dict], search_fn, k: int = 5) -> dict:
    """
    评估检索质量

    指标：
    - Recall@K: top-K 结果中包含预期来源的比例
    - MRR: 第一个正确结果的排名倒数的平均值
    """
    recall_hits = 0
    mrr_sum = 0.0
    total = len(dataset)

    for item in dataset:
        question = item["question"]
        expected_sources = set(item["expected_sources"])

        results = search_fn(question, k=k)
        result_sources = [
            doc.metadata.get("filename", "") for doc, _ in results
        ]

        # Recall@K
        if expected_sources & set(result_sources):
            recall_hits += 1

        # MRR
        for rank, source in enumerate(result_sources, 1):
            if source in expected_sources:
                mrr_sum += 1.0 / rank
                break

    return {
        f"Recall@{k}": recall_hits / total if total else 0,
        "MRR": mrr_sum / total if total else 0,
        "total_questions": total,
    }


def main():
    with_generation = "--with-generation" in sys.argv

    # 加载数据集
    dataset_path = Path(__file__).parent / "eval_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"📊 RAG 评估")
    print(f"   数据集: {len(dataset)} 个问题")
    print(f"   模式: {'检索 + 生成' if with_generation else '仅检索'}")
    print("=" * 50)

    # 检索评估
    from src.rag.hybrid_search import enhanced_search

    print("\n🔍 检索质量评估...")
    metrics_k5 = evaluate_retrieval(dataset, enhanced_search, k=5)
    metrics_k10 = evaluate_retrieval(dataset, enhanced_search, k=10)

    print(f"\n   Recall@5:  {metrics_k5['Recall@5']:.1%}")
    print(f"   Recall@10: {metrics_k10['Recall@10']:.1%}")
    print(f"   MRR:       {metrics_k5['MRR']:.3f}")

    if with_generation:
        print("\n📝 生成质量评估...")
        from src.rag.chain import rag_query
        correct = 0
        for item in dataset:
            result = rag_query(item["question"])
            answer = result["answer"].lower()
            keywords = item["expected_answer_keywords"]
            hits = sum(1 for kw in keywords if kw.lower() in answer)
            if hits >= len(keywords) * 0.4:
                correct += 1
        print(f"   回答质量 (关键词覆盖 ≥40%): {correct}/{len(dataset)} ({correct/len(dataset):.1%})")

    print("\n" + "=" * 50)
    print("✅ 评估完成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 创建评估说明文档**

创建 `evaluation/README.md`：

```markdown
# RAG 评估体系

## 评估数据集

`eval_dataset.json` 包含 20 组 Q&A 对，覆盖：
- 设备故障案例（制冰机、咖啡机、机械臂等）
- 技术文档查询（日志规范、状态机、版本同步等）
- 运维操作（OTA 升级、Docker 重启等）

## 运行评估

```bash
# 仅检索评估（不需要 LLM API key）
python evaluation/run_eval.py

# 检索 + 生成评估（需要配置 LLM API key）
python evaluation/run_eval.py --with-generation
```

## 评估指标

| 指标 | 说明 | 目标 |
|------|------|------|
| Recall@5 | top 5 结果命中预期来源的比例 | ≥ 70% |
| Recall@10 | top 10 结果命中预期来源的比例 | ≥ 85% |
| MRR | 首个正确结果排名倒数的均值 | ≥ 0.5 |
| 回答质量 | 关键词覆盖 ≥40% 的比例 | ≥ 60% |

## 添加新测试用例

在 `eval_dataset.json` 中添加条目：
```json
{
  "question": "用户可能问的问题",
  "expected_answer_keywords": ["关键词1", "关键词2"],
  "expected_sources": ["期望命中的文档文件名.md"]
}
```
```

- [ ] **Step 4: Commit**

```bash
git add evaluation/
git commit -m "feat: add RAG evaluation framework with 20 Q&A test cases"
```

---

## Task 9: 更新文档

**Files:**
- Modify: `README.md`
- Modify: `docs/usage-and-learning-guide.md`

- [ ] **Step 1: 更新 README.md**

在 README.md 中更新以下内容：

1. 功能列表中添加：
   - ✅ 检索质量优化（Reranking、混合检索）
   - ✅ RAG 评估（检索准确率、回答质量）

2. 工具列表更新为 6 个：
   - `search_knowledge_base` — 知识库检索（混合检索 + 重排序）
   - `fetch_device_logs` — 设备日志读取
   - `query_device_status` — 设备状态查询
   - `generate_diagnosis_report` — 诊断报告生成
   - `restart_device_service` — 设备服务重启
   - `check_firmware_version` — 固件版本检查

3. 新增 RAG 优化说明章节

- [ ] **Step 2: 更新 usage-and-learning-guide.md**

在 `docs/usage-and-learning-guide.md` 中添加 RAG 优化章节：

```markdown
## RAG 检索优化

### 混合检索架构

系统使用两路检索 + 融合 + 重排序的三阶段管道：

1. **向量语义检索** — ChromaDB/Milvus 相似度搜索（top 20）
2. **BM25 关键词检索** — 基于 TF-IDF 的传统检索（top 20）
3. **RRF 融合** — Reciprocal Rank Fusion 合并两路结果
4. **CrossEncoder 重排序** — 精排后返回 top 5

### 查询改写

可选功能，使用 LLM 将口语化描述转为结构化检索查询：
- "冰不够了" → "制冰机 出冰量不足 故障"

### 评估体系

```bash
# 运行检索评估
python evaluation/run_eval.py

# 运行完整评估（含生成质量）
python evaluation/run_eval.py --with-generation
```
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/usage-and-learning-guide.md
git commit -m "docs: update README and learning guide with RAG optimization and new tools"
```

---

## Task 10: 运行全部测试 + 代码审查

- [ ] **Step 1: 运行全部测试**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v --tb=short`
Expected: All tests PASSED

- [ ] **Step 2: 代码审查清单**

验证以下项目：
- [ ] `src/rag/reranker.py` — 线程安全单例、mock 接口清晰
- [ ] `src/rag/hybrid_search.py` — BM25 分词合理、RRF 公式正确、错误处理完备
- [ ] `src/tools/device_restart.py` — 命令白名单安全、无注入风险
- [ ] `src/tools/firmware_check.py` — 超时处理、离线降级
- [ ] `src/agent/diagnostic_agent.py` — 6 个工具正确注册
- [ ] `src/rag/chain.py` — enhanced_search 正确替换
- [ ] `src/tools/knowledge_search.py` — import 路径正确
- [ ] `evaluation/` — 数据集格式正确、脚本可运行
- [ ] `README.md` — 内容与实际一致
- [ ] 全部测试通过

- [ ] **Step 3: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete iteration 2 - RAG optimization, evaluation, new tools

Changes:
- CrossEncoder reranking (ms-marco-MiniLM-L-6-v2)
- BM25 + vector hybrid search with RRF fusion
- Optional query rewriting via LLM
- RAG evaluation framework (20 Q&A test cases)
- Device restart tool (SSH, command whitelist)
- Firmware version check tool (API)
- Agent expanded from 4 to 6 tools
- Updated README and learning guide"
```
