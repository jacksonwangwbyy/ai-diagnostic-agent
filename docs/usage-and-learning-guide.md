# SMYZE 智能设备故障诊断 Agent — 使用与学习指南

> 面向 Java 工程师的 AI 工程转型实战项目，从零到生产级。

---

## 第一部分：快速上手

### 1.1 环境准备

```bash
# 前提：已安装 Python 3.11+、Node.js 18+、Git

# 克隆项目
git clone https://github.com/jacksonwangwbyy/ai-diagnostic-agent.git
cd ai-diagnostic-agent

# 创建 Python 虚拟环境
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 安装 Python 依赖（首次约 5-10 分钟，sentence-transformers 较大）
pip install -r requirements.txt
```

### 1.2 配置 API Key

```bash
# 复制环境变量模板
cp .env.example .env
```

打开 `.env` 文件，**必须填入**以下两项：

```env
# 至少填一个 API key（建议两个都填，用于测试降级功能）
ANTHROPIC_API_KEY=sk-ant-...你的Claude密钥...
OPENAI_API_KEY=sk-...你的OpenAI密钥...

# 如果使用中转站，填入中转站地址
ANTHROPIC_BASE_URL=https://你的中转站地址
OPENAI_BASE_URL=https://你的中转站地址/v1
```

其他配置保持默认即可。

### 1.3 三种使用方式

#### 方式一：CLI 命令行（最快上手）

```bash
# Agent 模式（默认）— 可以调用工具、多步推理
python -m src.main

# 纯对话模式
python -m src.main --chat
```

**CLI 内置命令：**

| 命令 | 作用 |
|------|------|
| `/agent` | 切换到 Agent 诊断模式 |
| `/chat` | 切换到普通对话模式 |
| `/switch claude` | 切换到 Claude 模型 |
| `/switch openai` | 切换到 OpenAI 模型 |
| `/clear` | 清除对话历史 |
| `/quit` | 退出 |

**试一试：**

```
🧑 你: 制冰机报 E03 错误怎么处理？

🤖 [Thought] 需要先查询设备状态，再搜索知识库...
🔧 调用工具: query_device_status(module="制冰机")
🔧 工具结果: 状态=fault, 错误码=E03
🔧 调用工具: search_knowledge_base(query="制冰机 E03 错误")
🔧 工具结果: E03 = 制冰过程超时...
🤖 综合分析: E03 是制冰超时错误，可能原因是...
```

#### 方式二：API 服务 + React 前端

```bash
# 终端 1：启动后端 API
uvicorn src.api.app:app --reload --port 8000

# 终端 2：启动前端
cd frontend && npm install && npm run dev
```

然后：
- 前端界面：http://localhost:3000
- Swagger API 文档：http://localhost:8000/docs

**前端功能：**
- 左上角切换「Agent 诊断」和「普通对话」两种模式
- Agent 模式下可以看到实时的工具调用过程（SSE 流式推送）
- 普通对话模式下逐字输出（打字机效果）

#### 方式三：Docker 一键部署

```bash
docker compose up -d
# 包含：Agent 服务(8000) + Redis(6379) + Milvus(19530)
```

### 1.4 构建知识库（重要！）

RAG 检索和知识库搜索工具依赖知识库，**首次使用前必须构建**：

```bash
# 使用本地 Embedding 模型（离线，免费，首次会自动下载 ~90MB 模型）
python scripts/build_knowledge_base.py --local

# 或使用 OpenAI Embedding API（效果更好，需要 API key）
python scripts/build_knowledge_base.py
```

构建完成后会在项目根目录生成 `chroma_data/` 目录，后续启动时自动加载。

### 1.5 API 接口速查

| 方法 | 路径 | 用途 | 请求体示例 |
|------|------|------|-----------|
| POST | `/api/chat` | 普通对话 | `{"message": "你好", "provider": "claude", "session_id": "user1"}` |
| POST | `/api/chat/stream` | 普通对话(SSE) | 同上 |
| POST | `/api/diagnose` | Agent诊断 | `{"question": "制冰机E03报错", "provider": "claude"}` |
| POST | `/api/diagnose/stream` | Agent诊断(SSE) | 同上 |
| POST | `/api/rag/query` | RAG知识库问答 | `{"query": "制冰机清洗步骤", "top_k": 5}` |
| GET | `/api/sessions` | 列出活跃会话 | - |
| DELETE | `/api/session/{id}` | 清除会话 | - |
| GET | `/health` | 健康检查 | - |

**curl 测试示例：**

```bash
# 普通对话
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "provider": "claude"}'

# Agent 诊断
curl -X POST http://localhost:8000/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"question": "制冰机报E03错误怎么处理"}'

# RAG 知识库检索
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "冷藏柜温度异常"}'

# SSE 流式（用 curl 看原始 SSE 事件流）
curl -N -X POST http://localhost:8000/api/diagnose/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "设备状态检查"}'
```

---

## 第二部分：代码学习路线

### 建议阅读顺序

每个源文件顶部都有 `"""学习要点"""` 注释，按以下顺序阅读，知识点递进：

```
第一层：基础设施
├── 1. src/config/settings.py          ← 先看配置，了解全局参数
├── 2. src/llm/client.py               ← LLM 接入的核心，理解 ChatModel
│
第二层：RAG 知识库（数据侧）
├── 3. src/rag/loader.py               ← 文档加载，理解 Document 对象
├── 4. src/rag/splitter.py             ← 文本切分，理解 chunk 策略
├── 5. src/rag/vectorstore.py          ← 向量存储，理解 Embedding + 相似度检索
├── 6. src/rag/chain.py                ← RAG 链，理解"检索 + 生成"串联
│
第三层：Agent 工具调用
├── 7. src/tools/knowledge_search.py   ← @tool 装饰器，最简单的工具
├── 8. src/tools/log_reader.py         ← 复杂工具：双模式 + 输入校验
├── 9. src/tools/device_status.py      ← 外部 API 工具
├──10. src/tools/diagnosis_report.py   ← 输出类工具
├──11. src/agent/diagnostic_agent.py   ← Agent 编排核心，理解 ReAct
│
第四层：生产化
├──12. src/api/models.py               ← Pydantic 数据模型
├──13. src/api/routes.py               ← API + SSE 流式
├──14. src/api/app.py                  ← FastAPI 应用
├──15. src/utils/session_store.py      ← Redis 会话持久化
├──16. frontend/src/App.tsx            ← React + SSE 前端
```

### 2.1 LLM 接入层 — `src/llm/client.py`

**你将学到：** LangChain ChatModel、消息类型、流式输出、多模型降级

**核心概念：**

```
LangChain 消息类型（对应 LLM API 的 role）:
┌─────────────────┬───────────────┬────────────────────────────┐
│ LangChain 类    │ API role      │ 用途                        │
├─────────────────┼───────────────┼────────────────────────────┤
│ SystemMessage   │ system        │ 系统提示词，定义 AI 的角色   │
│ HumanMessage    │ user          │ 用户输入                    │
│ AIMessage       │ assistant     │ AI 回复                     │
└─────────────────┴───────────────┴────────────────────────────┘

多轮对话原理：把完整消息历史传给 LLM
history = [
    SystemMessage("你是诊断助手"),     # 始终在最前面
    HumanMessage("制冰机报错"),        # 第1轮用户
    AIMessage("请描述具体错误码"),      # 第1轮AI回复
    HumanMessage("E03"),               # 第2轮用户  ← 新消息
]
response = llm.invoke(history)         # LLM 看到完整上下文
```

**降级链机制（重点学习）：**

```python
# client.py 第84行
primary.with_fallbacks([fallback])

# 效果：
# 1. 先调用 primary（如 Claude）
# 2. 如果 Claude 抛异常（网络超时、API 限流、余额不足等）
# 3. 自动切换到 fallback（如 OpenAI）重试
# 4. 调用方完全无感知（同一个 invoke/stream 接口）
```

**Java 对照理解：**

| Python / LangChain | Java 类比 |
|---------------------|-----------|
| `create_llm()` | `@Bean ChatClient` 工厂方法 |
| `llm.invoke(messages)` | `chatClient.call(prompt)` |
| `llm.stream(messages)` | `chatClient.stream(prompt)` → `Flux<String>` |
| `with_fallbacks()` | Spring Retry + Fallback |
| `DiagnosticChat` | 有状态的 Service Bean |

### 2.2 RAG 知识库 — `src/rag/`

**你将学到：** 文档加载、文本切分策略、Embedding、向量检索、RAG 链

**RAG 全流程图：**

```
离线构建（一次性）:
  device-manuals/*.md ──→ load_directory() ──→ [Document, ...]
                              ↓
                     split_documents()
                     Markdown: 标题切分 → 字符切分（二次策略）
                     PDF:      字符切分
                              ↓
                     [chunk1, chunk2, ...] (800字/块, 150字重叠)
                              ↓
                     create_vector_store(documents)
                     Embedding: "制冰机E03" → [0.12, -0.34, 0.56, ...]
                              ↓
                     ChromaDB / Milvus 持久化存储

在线检索（每次请求）:
  用户问题: "制冰机E03报错"
       ↓ Embedding
  查询向量: [0.11, -0.33, 0.55, ...]
       ↓ 余弦相似度搜索 top-5
  检索结果: [(Doc1, 0.23), (Doc2, 0.45), ...]
       ↓ format_context() 格式化
  注入 Prompt:
       System: "参考以下文档回答... {context}"
       Human: "制冰机E03报错怎么处理？"
       ↓ LLM 生成
  回答: "E03 是制冰超时错误，根据设备手册..."
       + 引用来源: [ice-manual.md, fault-E03.md]
```

**文本切分为什么重要：**

```
chunk_size 太大（如 5000）:
  → 检索时匹配到的文档太泛，包含大量无关内容
  → LLM 被噪音干扰，回答质量下降

chunk_size 太小（如 100）:
  → 上下文被切碎，丢失段落语义
  → "E03错误码" 和 "处理方法" 可能被切到不同块

本项目选择 chunk_size=800, overlap=150:
  → 一个 chunk 约 1-2 个自然段，保持语义完整
  → 150字重叠确保边界处的句子不被截断
```

**Embedding 选型对照：**

| 模型 | 维度 | 中文效果 | 成本 | 适用 |
|------|------|---------|------|------|
| `all-MiniLM-L6-v2` | 384 | 一般 | 免费离线 | 开发/演示 |
| `text-embedding-3-small` | 1536 | 好 | $0.02/1M tokens | 生产 |
| `bge-large-zh` | 1024 | 优秀 | 免费离线 | 中文生产推荐 |

### 2.3 Agent 工具调用 — `src/tools/` + `src/agent/`

**你将学到：** @tool 装饰器、Function Calling、ReAct 推理循环

**@tool 装饰器的魔法：**

```python
@tool
def search_knowledge_base(query: str) -> str:
    """搜索设备知识库，查找设备手册、故障案例等技术文档。"""
    ...

# LangChain 自动提取为：
# Tool(
#     name = "search_knowledge_base",        ← 函数名
#     description = "搜索设备知识库...",       ← docstring
#     args_schema = {"query": {"type": "str"}} ← 参数签名
# )
```

**Agent 决策的核心：LLM 看到工具列表后自主选择**

```
System Prompt:
  你有以下工具可用：
  1. search_knowledge_base(query) - 搜索设备知识库...
  2. fetch_device_logs(log_type, lines, keyword) - 读取设备日志...
  3. query_device_status(module) - 查询设备状态...
  4. generate_diagnosis_report(...) - 生成诊断报告...

User: 制冰机报E03错误

LLM 思考过程:
  → "用户问的是制冰机故障，我需要先查状态"
  → 生成 tool_calls: [{"name": "query_device_status", "args": {"module": "制冰机"}}]
  → 收到 ToolMessage 结果后继续推理
  → "状态是 fault，E03 错误码，我需要查知识库了解 E03 含义"
  → 生成 tool_calls: [{"name": "search_knowledge_base", "args": {"query": "E03"}}]
  → ... 循环直到信息足够，输出最终回答
```

**ReAct 循环图解：**

```
                    ┌──────────────────────────┐
                    │    LLM 推理 (Thought)     │
                    │    分析当前信息，决定下一步  │
                    └──────────┬───────────────┘
                               │
               ┌───────────────┼───────────────┐
               │ 有 tool_calls │               │ 无 tool_calls
               ▼               │               ▼
     ┌─────────────────┐       │     ┌─────────────────┐
     │  执行工具 (Act)   │       │     │  输出结论 (End)   │
     │  运行对应函数     │       │     │  返回最终回答     │
     └────────┬────────┘       │     └─────────────────┘
              │ ToolMessage     │
              └────────────────┘
                  (循环)
```

**Java 对照理解：**

| Python / LangChain | Java 类比 |
|---------------------|-----------|
| `@tool` | Spring AI 的 `@Tool` 注解 / LangChain4j 的 `@Tool` |
| `create_react_agent()` | LangChain4j `AiServices.builder().tools(...)` |
| `agent.invoke()` | `aiService.chat()` 触发推理链 |
| `agent.stream()` | `aiService.chatStream()` 逐步输出 |
| `TOOLS` 列表 | Spring AI `FunctionCallback` 列表 |

### 2.4 API 与流式输出 — `src/api/`

**你将学到：** FastAPI、SSE、Pydantic、会话管理

**SSE 流式输出原理：**

```
客户端                                         服务端
  │                                              │
  │── POST /api/diagnose/stream ──────────────→ │
  │                                              │ agent.stream() 开始
  │                                              │
  │ ←── data: {"type":"tool_call","tool":"..."} ─│ LLM 决定调用工具
  │ ←── data: {"type":"tool_result","result":..} │ 工具执行完毕
  │ ←── data: {"type":"tool_call","tool":"..."} ─│ LLM 决定调用下一个
  │ ←── data: {"type":"tool_result","result":..} │
  │ ←── data: {"type":"answer","content":"..."} ─│ LLM 输出最终结论
  │ ←── data: {"type":"done"} ───────────────── │ 完成
  │                                              │
```

**Java 对照理解：**

| Python / FastAPI | Java / Spring 类比 |
|---|---|
| `FastAPI()` | `@SpringBootApplication` |
| `@router.post("/chat")` | `@PostMapping("/chat")` |
| `StreamingResponse` | `SseEmitter` / `Flux<ServerSentEvent>` |
| `BaseModel` (Pydantic) | `@Data` (Lombok) + `@Valid` |
| `APIRouter` | `@RestController` |
| `uvicorn` | 内嵌 Tomcat |

### 2.5 会话持久化 — `src/utils/session_store.py`

**你将学到：** Redis 序列化、降级策略、缓存分层

**三级查找策略：**

```
请求: _store.get("user123", "claude")

  ①  内存缓存有 "user123"？ ──→ 有 → 直接返回（最快，< 1ms）
         │ 没有
         ▼
  ②  Redis 有 "agent:session:user123"？ ──→ 有 → 反序列化 → 缓存到内存 → 返回
         │ 没有
         ▼
  ③  新建 DiagnosticChat → 存 Redis → 缓存到内存 → 返回
```

**LangChain 消息序列化：**

```python
# DiagnosticChat 在内存中:
chat.history = [
    SystemMessage(content="你是诊断助手"),
    HumanMessage(content="制冰机报错"),
    AIMessage(content="请描述具体错误码"),
]

# 序列化到 Redis:
{
    "provider": "claude",
    "messages": [
        {"type": "system", "content": "你是诊断助手"},
        {"type": "human", "content": "制冰机报错"},
        {"type": "ai", "content": "请描述具体错误码"}
    ]
}
```

---

## 第三部分：架构全景

### 3.1 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    用户层                                │
│  ┌──────────┐    ┌──────────────┐    ┌────────────────┐ │
│  │ CLI 终端  │    │ React 前端   │    │ curl / Postman │ │
│  │ main.py  │    │ App.tsx      │    │                │ │
│  └────┬─────┘    └──────┬───────┘    └───────┬────────┘ │
│       │                 │ Vite Proxy          │          │
└───────┼─────────────────┼─────────────────────┼──────────┘
        │                 │                     │
┌───────▼─────────────────▼─────────────────────▼──────────┐
│                  FastAPI 服务层 (8000)                     │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  routes.py                                          │ │
│  │  /chat  /chat/stream  /diagnose  /diagnose/stream   │ │
│  │  /rag/query  /sessions  /session/{id}               │ │
│  └──────────┬───────────────┬──────────────┬───────────┘ │
│             │               │              │             │
│  ┌──────────▼──┐  ┌────────▼────────┐  ┌──▼─────────┐  │
│  │Diagnostic   │  │ diagnostic_     │  │ rag_query  │  │
│  │Chat (对话)  │  │ agent (Agent)   │  │ (RAG检索)  │  │
│  └──────┬──────┘  └───────┬─────────┘  └──────┬─────┘  │
│         │                 │                    │        │
│  ┌──────▼─────────────────▼────────────────────▼──────┐ │
│  │              create_llm() + with_fallbacks()       │ │
│  │          Claude ←──降级──→ OpenAI                   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌──────────────── Agent 工具箱 ────────────────────┐   │
│  │ query_device_status  │ fetch_device_logs          │   │
│  │ search_knowledge_base│ generate_diagnosis_report  │   │
│  └──────────┬───────────┴────────────┬───────────────┘   │
│             │                        │                   │
└─────────────┼────────────────────────┼───────────────────┘
              │                        │
    ┌─────────▼─────────┐    ┌────────▼────────────┐
    │ bar_middleware API │    │ 向量数据库            │
    │ (设备状态/日志)    │    │ ChromaDB / Milvus    │
    └───────────────────┘    └──────────────────────┘
              │                        │
    ┌─────────▼─────────┐    ┌────────▼────────────┐
    │ Redis (会话存储)   │    │ knowledge-base/     │
    │ 自动降级到内存     │    │ 14个设备文档         │
    └───────────────────┘    └──────────────────────┘
```

### 3.2 核心设计模式

| 模式 | 实现位置 | Java 类比 |
|------|---------|-----------|
| **工厂模式** | `create_llm()` / `create_vector_store()` | `@Bean` + `@ConditionalOnProperty` |
| **三层降级** | LLM fallback / Redis→内存 / 流式→非流式 | Spring Retry + Fallback |
| **单例+双重检查锁** | `vectorstore._cached_vectorstore` | `DCL Singleton` |
| **策略模式** | `LOG_READ_MODE: local/ssh` | `@ConditionalOnProperty` + 接口多实现 |
| **装饰器** | `@tool` 注册工具 | `@Tool` 注解 |
| **ReAct Agent** | `create_react_agent()` | LangChain4j `AiServices` |
| **SSE 流式** | `StreamingResponse` + generator | `SseEmitter` / `Flux<SSE>` |

### 3.3 配置切换总览

```env
# 切换 LLM
DEFAULT_LLM_PROVIDER=claude        # 或 openai
LLM_FALLBACK_ENABLED=true          # 主模型失败自动切备用

# 切换向量数据库
VECTOR_DB_TYPE=chromadb             # 开发用 chromadb，生产用 milvus

# 切换日志读取模式
LOG_READ_MODE=local                 # 同机部署用 local，跨机用 ssh

# 切换会话存储
REDIS_URL=redis://localhost:6379/0  # 留空则自动降级到内存存储
```

---

## 第四部分：动手练习

### 练习 1：跑通完整流程

1. 配置 `.env`，启动 CLI：`python -m src.main`
2. 输入 `/chat` 切换到对话模式，和 AI 聊天
3. 输入 `/agent` 切换到 Agent 模式，提问"制冰机报错了"
4. 观察 Agent 自主调用了哪些工具

### 练习 2：理解 RAG

1. 运行 `python scripts/build_knowledge_base.py --local`
2. 观察输出：加载了多少文档、切了多少块
3. 启动 API，调用 `/api/rag/query`，看检索结果和引用来源
4. 修改 `splitter.py` 的 `chunk_size`（改为 300 和 1500），重新构建，对比检索效果

### 练习 3：写一个新工具

在 `src/tools/` 下创建 `network_check.py`：

```python
from langchain_core.tools import tool

@tool
def check_network_status(target: str = "baidu.com") -> str:
    """检查设备的网络连通性。当怀疑设备离线或网络异常时使用此工具。"""
    import subprocess
    result = subprocess.run(
        ["ping", "-n", "3", target],  # Windows用-n，Linux用-c
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        return f"网络正常，ping {target} 成功:\n{result.stdout}"
    return f"网络异常，无法 ping 通 {target}"
```

然后在 `diagnostic_agent.py` 的 TOOLS 列表中注册它，重启服务测试。

### 练习 4：前端 SSE 流式

1. 启动后端 + 前端
2. 在前端选择 Agent 模式，提问
3. 打开浏览器 DevTools → Network → 找到 `diagnose/stream` 请求
4. 观察 EventStream 中逐步推送的 `tool_call` → `tool_result` → `answer` → `done`

### 练习 5：对比 Java 实现

用 Spring AI / LangChain4j 实现同样的功能，体会差异：

| 功能 | Python 实现 | Java 对应方案 |
|------|------------|---------------|
| LLM 调用 | `langchain-anthropic` | `spring-ai-anthropic` |
| RAG | `langchain-chroma` | `spring-ai-chroma` |
| Agent | `langgraph.create_react_agent` | `langchain4j AiServices` |
| 流式 | `StreamingResponse` SSE | `SseEmitter` / WebFlux |
| 向量库 | ChromaDB / Milvus | 同 |

---

## 第五部分：关键文件速查表

| 文件 | 一句话职责 | 核心 API |
|------|----------|---------|
| `settings.py` | 全局配置单例 | `settings.XXX` |
| `client.py` | LLM 工厂 + 多轮对话 | `create_llm()` / `DiagnosticChat` / `extract_text()` |
| `loader.py` | 文档加载 | `load_directory(path) → [Document]` |
| `splitter.py` | 文本切分 | `split_documents(docs) → [chunk]` |
| `vectorstore.py` | 向量存储与检索 | `search(query, k)` / `search_with_scores(query, k)` |
| `chain.py` | RAG 检索+生成 | `rag_query(question) → {answer, sources}` |
| `knowledge_search.py` | Agent 工具：知识库 | `search_knowledge_base(query)` |
| `log_reader.py` | Agent 工具：日志 | `fetch_device_logs(log_type, lines, keyword)` |
| `device_status.py` | Agent 工具：设备状态 | `query_device_status(module)` |
| `diagnosis_report.py` | Agent 工具：报告 | `generate_diagnosis_report(...)` |
| `device_restart.py` | Agent 工具：服务重启 | `restart_device_service(service)` |
| `firmware_check.py` | Agent 工具：版本检查 | `check_firmware_version(component)` |
| `reranker.py` | CrossEncoder 重排序 | `rerank(query, docs, top_k)` |
| `hybrid_search.py` | 混合检索入口 | `enhanced_search(query, k)` / `BM25Index` / `rrf_fuse()` |
| `repair_agent.py` | 维修建议 Agent | `create_repair_agent()` |
| `monitor_agent.py` | 设备监控 Agent | `create_monitor_agent()` |
| `supervisor.py` | 多 Agent 编排 | `run_multi_agent(question)` |
| `diagnostic_agent.py` | Agent 编排核心 | `create_diagnostic_agent()` / `run_diagnosis()` |
| `app.py` | FastAPI 入口 | `app` |
| `limiter.py` | API 限流单例 | `limiter`（slowapi） |
| `models.py` | 请求/响应模型 | `ChatRequest` / `DiagnoseResponse` / `RAGQueryResponse` |
| `routes.py` | API 路由 | 7 个 REST 接口 |
| `session_store.py` | 会话持久化 | `create_session_store()` / `RedisSessionStore` |
| `main.py` | CLI 入口 | `python -m src.main` |
| `build_knowledge_base.py` | 知识库构建 | `python scripts/build_knowledge_base.py --local` |
| `App.tsx` | React 前端 | SSE 流式解析 + 消息渲染 |
| `run_eval.py` | RAG 评估脚本 | `python evaluation/run_eval.py` |

---

## 第七部分：多 Agent 协作系统

### 7.1 架构

```
用户请求 → Supervisor（意图识别 + 路由）
                ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
 诊断 Agent  维修 Agent  监控 Agent
 (6个工具)   (知识库+报告) (状态+日志+版本)
```

### 7.2 路由策略

| 关键词 | 路由 |
|--------|------|
| 故障/报错/不工作 | diagnose（诊断 Agent） |
| 维修/怎么修/备件 | repair（维修 Agent） |
| 状态/健康/检查 | monitor（监控 Agent） |
| 故障 + 维修 | diagnose+repair（链式） |

### 7.3 使用方式

**API 调用（多 Agent 模式）：**
```bash
curl -X POST http://localhost:8000/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"question": "制冰机故障了，怎么修", "use_multi_agent": true}'
```

**Python 直接调用：**
```python
from src.agent.supervisor import run_multi_agent

result = run_multi_agent("检查所有设备状态")
print(result["route"])        # "monitor"
print(result["agents_used"])  # ["monitor"]
print(result["result"])       # 设备健康状态汇总
```

---

## 第六部分：RAG 检索优化

### 6.1 混合检索架构

系统使用两路检索 + 融合 + 重排序的三阶段管道：

```
用户问题 → [查询改写(可选)] → 向量语义检索(top 20) + BM25关键词检索(top 20)
                                        ↓
                                  RRF 融合(top 20)
                                        ↓
                              CrossEncoder 重排序(top 5)
                                        ↓
                                  LLM 生成回答
```

### 6.2 核心组件

| 组件 | 文件 | 说明 |
|------|------|------|
| CrossEncoder | `src/rag/reranker.py` | `cross-encoder/ms-marco-MiniLM-L-6-v2`，本地运行，约 80MB |
| BM25 索引 | `src/rag/hybrid_search.py` | 基于 `rank-bm25` 库，中文字符级 + 2-gram 分词 |
| RRF 融合 | `src/rag/hybrid_search.py` | `score = sum(1/(k+rank))`，k=60 |
| 查询改写 | `src/rag/hybrid_search.py` | LLM 将口语化描述转为结构化查询（可选） |

### 6.3 评估体系

```bash
# 仅检索评估（不需要 LLM API key）
python evaluation/run_eval.py

# 检索 + 生成评估（需要配置 LLM API key）
python evaluation/run_eval.py --with-generation
```

评估指标：Recall@5、Recall@10、MRR、回答质量（关键词覆盖率）。
评估数据集：`evaluation/eval_dataset.json`（20 组 Q&A 对）。