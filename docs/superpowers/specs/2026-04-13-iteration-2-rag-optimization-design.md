# 迭代 2：RAG 优化 & 评估 + 新诊断工具 设计方案

> 日期: 2026-04-13
> 状态: 已确认
> 前置: 迭代 1 已完成（代码清理、故障案例、测试套件）

## 概述

提升 RAG 检索质量，建立自动评估体系，新增 2 个诊断工具，同步更新文档。

---

## 2.1 检索质量优化

### 架构

在现有向量检索和 LLM 生成之间插入三个优化步骤：

```
用户问题
  ↓
查询改写（LLM 将口语化描述转为结构化查询）
  ↓
┌─────────────────┬──────────────────┐
│ 向量语义检索     │ BM25 关键词检索   │
│ (top 20)        │ (top 20)         │
└────────┬────────┴────────┬─────────┘
         │    RRF 融合      │
         └────────┬─────────┘
                  ↓
         CrossEncoder 重排序
                  ↓
              Top 5 结果
                  ↓
           LLM 生成回答
```

### Reranker

- 模型: `cross-encoder/ms-marco-MiniLM-L-6-v2`（约 80MB，本地运行）
- 输入: (query, document) 对
- 输出: 相关性分数 0-1
- 对初次检索的 top 20 结果重排序，取 top 5

### 混合检索

- 语义检索: 现有 ChromaDB/Milvus 向量搜索
- 关键词检索: BM25（使用 rank-bm25 库）
- 融合策略: Reciprocal Rank Fusion (RRF)
  - `score = sum(1 / (k + rank_i))` 其中 k=60
- BM25 索引在知识库构建时一次性创建，缓存在内存中

### 查询改写

- 使用现有 LLM 将用户口语化描述转为结构化查询
- 示例: "冰不够了" → "制冰机 出冰量不足 故障"
- 可选步骤，通过配置开关控制

### 新增文件

| 文件 | 职责 |
|------|------|
| `src/rag/reranker.py` | CrossEncoder 重排序 |
| `src/rag/hybrid_search.py` | BM25 索引 + 混合检索 + 查询改写 + RRF 融合 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `src/rag/chain.py` | `rag_query` 和 `rag_stream` 使用新的混合检索管道 |
| `src/tools/knowledge_search.py` | 使用新检索管道替代直接 `search_with_scores` |
| `requirements.txt` | 添加 `rank-bm25>=0.2,<0.3` |

### 接口设计

```python
# src/rag/reranker.py
def create_reranker() -> CrossEncoder
def rerank(query: str, documents: list[Document], top_k: int = 5) -> list[Document]

# src/rag/hybrid_search.py
class HybridSearcher:
    def __init__(self, documents: list[Document])
    def bm25_search(self, query: str, k: int = 20) -> list[Document]
    def hybrid_search(self, query: str, k: int = 5) -> list[tuple[Document, float]]

def rewrite_query(question: str, llm) -> str
def enhanced_search(query: str, k: int = 5) -> list[tuple[Document, float]]
```

---

## 2.2 RAG 评估体系

### 评估数据集

- 20 组 Q&A 对，基于现有 14 份设备手册 + 25 个故障案例
- 格式: JSON，每条包含 question、expected_answer、expected_sources

### 评估指标

| 指标 | 说明 |
|------|------|
| Recall@5 | top 5 结果中包含正确文档的比例 |
| Recall@10 | top 10 结果中包含正确文档的比例 |
| MRR | 第一个正确结果的排名倒数的平均值 |
| 回答质量 | 使用 LLM 对比生成回答与参考答案的语义相似度（0-5 分） |

### 新增文件

| 文件 | 职责 |
|------|------|
| `evaluation/eval_dataset.json` | 评估数据集（20 组 Q&A） |
| `evaluation/run_eval.py` | 自动评估脚本 |
| `evaluation/README.md` | 评估使用说明 |

---

## 2.3 新增诊断工具

### 设备重启工具

- 通过 SSH 发送重启命令到设备
- 支持重启指定服务（bar_middleware、bar-deploy-client）或整机重启
- 安全校验: 命令白名单，不允许任意命令执行

### 固件版本检查工具

- 通过 bar_middleware API 查询当前固件/软件版本
- 对比已知最新版本，提示是否需要升级

### 新增文件

| 文件 | 职责 |
|------|------|
| `src/tools/device_restart.py` | 设备/服务重启工具 |
| `src/tools/firmware_check.py` | 固件版本检查工具 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `src/agent/diagnostic_agent.py` | TOOLS 列表添加 2 个新工具 |

---

## 2.4 文档同步

| 文件 | 更新内容 |
|------|----------|
| `README.md` | 更新功能列表（RAG 优化、新工具）、更新工具列表（6 个）、标记已完成项 |
| `docs/usage-and-learning-guide.md` | 添加 RAG 优化章节（Reranking、混合检索、查询改写）、评估体系使用说明 |

---

## 2.5 测试

| 测试文件 | 覆盖 |
|----------|------|
| `tests/test_reranker.py` | CrossEncoder 加载、重排序逻辑 |
| `tests/test_hybrid_search.py` | BM25 搜索、RRF 融合、查询改写 |
| `tests/test_device_restart.py` | 重启命令白名单、SSH 调用 |
| `tests/test_firmware_check.py` | API 查询、版本对比 |

---

## 技术决策

| 决策 | 选择 | 原因 |
|------|------|------|
| Reranking 方案 | 本地 CrossEncoder | 零成本、内网可用、技术栈一致 |
| CrossEncoder 模型 | ms-marco-MiniLM-L-6-v2 | 轻量（80MB）、效果好、社区广泛使用 |
| BM25 实现 | rank-bm25 库 | 纯 Python、轻量、无外部依赖 |
| 融合策略 | RRF (k=60) | 简单有效、不需要调参、业界标准 |
| 评估方式 | 脚本化自动评估 | 可重复运行、CI 集成友好 |
