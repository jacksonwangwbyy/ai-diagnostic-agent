# 从零构建 AI 故障诊断 Agent —— 完整学习指南

> 这篇文档记录了如何用 Python + LangChain + RAG + LangGraph 从零搭建一个能自主调用工具、多步推理的智能设备故障诊断系统。
> 适合有 Python 基础、想入门 LLM 应用开发的同学。

---

## 项目是什么

一句话：**一个能像运维工程师一样排查设备故障的 AI Agent。**

它能做到：
- 接收用户描述的故障现象（"制冰机报错 E03"）
- 自主查询设备状态、读取日志、检索知识库
- 综合分析后生成结构化的诊断报告

不是简单的问答机器人，而是一个有"手"（工具）有"脑"（LLM 推理）的 Agent。

---

## 技术栈一览

| 层级 | 技术 | 作用 |
|------|------|------|
| LLM | Claude / GPT-4o | 大脑，负责推理和生成 |
| 框架 | LangChain | LLM 应用开发框架，统一接口 |
| Agent | LangGraph (ReAct) | Agent 编排，自主决策调用工具 |
| 知识库 | ChromaDB + Embedding | 向量检索，让 AI 能查文档 |
| API | FastAPI + SSE | 对外提供 REST 接口和流式输出 |
| 部署 | Docker + docker-compose | 一键部署 |

---

## 项目结构

```
ai-diagnostic-agent/
├── src/
│   ├── config/settings.py          # 配置管理
│   ├── llm/client.py               # LLM 客户端（双模型）
│   ├── rag/
│   │   ├── loader.py               # 文档加载
│   │   ├── splitter.py             # 文本切分
│   │   ├── vectorstore.py          # 向量存储
│   │   └── chain.py                # RAG 检索链
│   ├── tools/
│   │   ├── knowledge_search.py     # 知识库检索工具
│   │   ├── log_reader.py           # SSH 日志读取工具
│   │   ├── device_status.py        # 设备状态查询工具
│   │   └── diagnosis_report.py     # 诊断报告生成工具
│   ├── agent/diagnostic_agent.py   # ReAct Agent 编排
│   ├── api/                        # FastAPI 服务
│   └── main.py                     # CLI 入口
├── knowledge-base/                 # 设备手册和故障案例
├── scripts/build_knowledge_base.py # 知识库构建脚本
├── Dockerfile
└── docker-compose.yml
```

---

## Phase 1：LLM 基础接入

> 目标：让程序能调用 Claude/GPT，实现多轮对话。

### 核心概念

LangChain 把不同厂商的 LLM 统一成了相同的接口。不管你用 Claude 还是 GPT，调用方式都一样：

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

# 两个不同的模型，但接口完全一致
llm = ChatAnthropic(model="claude-sonnet-4-20250514", api_key="...")
llm = ChatOpenAI(model="gpt-4o", api_key="...")

# 调用方式一样
response = llm.invoke([HumanMessage(content="你好")])
```

### 关键代码：`src/llm/client.py`

```python
def create_llm(provider: str = None):
    """工厂函数：根据 provider 创建对应的 LLM 实例"""
    provider = provider or settings.DEFAULT_LLM_PROVIDER

    if provider == "claude":
        kwargs = {
            "model": settings.CLAUDE_MODEL,
            "api_key": settings.ANTHROPIC_API_KEY,
            "max_tokens": 4096,
        }
        if settings.ANTHROPIC_BASE_URL:
            kwargs["base_url"] = settings.ANTHROPIC_BASE_URL  # 支持中转站
        return ChatAnthropic(**kwargs)

    elif provider == "openai":
        kwargs = {
            "model": settings.OPENAI_MODEL,
            "api_key": settings.OPENAI_API_KEY,
        }
        if settings.OPENAI_BASE_URL:
            kwargs["base_url"] = settings.OPENAI_BASE_URL
        return ChatOpenAI(**kwargs)
```

### 消息类型

LangChain 用三种消息类型来表示对话：

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage(content="你是一个设备诊断助手"),  # 系统提示词，定义 AI 的角色
    HumanMessage(content="制冰机报错了"),           # 用户输入
    AIMessage(content="请问是什么错误码？"),         # AI 回复
    HumanMessage(content="E03"),                    # 用户继续
]

# 把整个消息列表传给 LLM，它就能理解上下文
response = llm.invoke(messages)
```

### 流式输出

用户体验的关键 —— 不用等 AI 想完再一次性显示，而是逐字输出：

```python
for chunk in llm.stream(messages):
    print(chunk.content, end="", flush=True)  # 逐 token 打印
```

### 学到了什么

- LangChain 的 ChatModel 抽象：统一接口，切换模型只需改一行
- 消息历史管理：多轮对话的本质就是维护一个消息列表
- 流式输出：`stream()` 方法，逐 token 返回
- 中转站配置：国内访问 Claude/GPT 的实际方案

---

## Phase 2：RAG 知识库构建

> 目标：让 AI 能查阅设备手册和故障案例，而不是只靠自己的知识瞎猜。

### RAG 是什么

RAG = Retrieval-Augmented Generation（检索增强生成）

核心思路：**先搜索，再回答。**

```
用户提问 → 从知识库检索相关文档 → 把文档塞进 Prompt → LLM 基于文档生成回答
```

为什么需要 RAG？因为 LLM 不知道你公司的设备手册内容。RAG 让它能"开卷考试"。

### Step 1：文档加载 (`loader.py`)

把各种格式的文件统一加载成 LangChain 的 `Document` 对象：

```python
from langchain_core.documents import Document

# Document 就两个字段：内容 + 元数据
doc = Document(
    page_content="制冰机错误码 E03 表示...",
    metadata={
        "source": "设备手册.md",
        "filename": "设备手册.md",
        "file_type": "markdown",
    }
)
```

支持 `.md`、`.pdf`、`.txt` 三种格式。PDF 按页加载，每页一个 Document。

### Step 2：文本切分 (`splitter.py`)

为什么要切分？因为一篇 5000 字的文档直接做 Embedding 效果很差。切成小块后，检索更精确。

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

# 通用切分器：按段落 → 换行 → 句号 → 空格的优先级切分
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # 每块最多 1000 字符
    chunk_overlap=200,    # 相邻块重叠 200 字符，避免切断语义
    separators=["\n\n", "\n", "。", "；", " ", ""],
)
```

对 Markdown 文件，我们用了二次切分策略：

```python
# 第一次：按标题切分（保持章节完整性）
md_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
)

# 第二次：对过长的 section 再按字符切分
final_chunks = text_splitter.split_documents(md_chunks)
```

### Step 3：向量存储 (`vectorstore.py`)

Embedding 就是把文本变成一个高维向量（一串数字）。语义相似的文本，向量距离近。

```python
# 本地 Embedding（免费离线）
from langchain_community.embeddings import HuggingFaceEmbeddings
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 存入 ChromaDB
from langchain_chroma import Chroma
vectorstore = Chroma.from_documents(
    documents=chunks,           # 切分后的文档块
    embedding=embedding,        # Embedding 模型
    persist_directory="./chroma_data",  # 持久化到磁盘
)

# 检索：输入问题，返回最相似的 5 个文档块
results = vectorstore.similarity_search_with_score("制冰机 E03 错误", k=5)
```

### Step 4：RAG 检索链 (`chain.py`)

把检索和生成串起来：

```python
def rag_query(question: str) -> dict:
    # 1. 检索相关文档
    results = search_with_scores(question, k=5)

    # 2. 格式化为上下文
    context = format_context(results)

    # 3. 构造 Prompt（把文档塞进去）
    messages = [
        SystemMessage(content=f"根据以下文档回答问题：\n{context}"),
        HumanMessage(content=question),
    ]

    # 4. LLM 生成回答
    response = llm.invoke(messages)

    return {"answer": response.content, "sources": [...]}
```

### 一键构建知识库

```bash
# 把 knowledge-base/ 目录下的文档全部加载、切分、Embedding、存入 ChromaDB
python scripts/build_knowledge_base.py --local
```

### 学到了什么

- RAG 的完整流程：加载 → 切分 → Embedding → 存储 → 检索 → 生成
- chunk_size 和 chunk_overlap 的权衡：太大检索不精确，太小丢失上下文
- Embedding 选型：本地模型（免费离线）vs OpenAI API（效果好但要钱）
- ChromaDB：轻量级向量数据库，开发阶段够用

---

## Phase 3：Agent & Function Calling

> 目标：让 AI 不只是回答问题，而是能自主调用工具来收集信息、分析问题。

### Agent vs Chain

这是最关键的概念区分：

```
Chain（链）：固定流程
  用户提问 → 检索文档 → 生成回答
  每次都走一样的路径，不管问题是什么。

Agent（智能体）：动态决策
  用户提问 → AI 思考 → 决定调用哪个工具 → 观察结果 → 继续思考 → ...
  根据问题不同，走不同的路径。
```

### ReAct 模式

ReAct = Reasoning + Acting（推理 + 行动）

```
Thought: 用户说制冰机报错 E03，我需要先查设备状态
Action:  调用 query_device_status("BAR-001")
Observation: 制冰机状态 error，错误码 E03

Thought: 我需要查日志看看具体错误信息
Action:  调用 fetch_device_logs("middleware", keyword="E03")
Observation: [2026-04-09 14:25] ICE_MACHINE: Error E03 - 水泵压力异常

Thought: 我需要查知识库看看 E03 的处理方法
Action:  调用 search_knowledge_base("制冰机 E03 水泵压力")
Observation: 根据设备手册，E03 表示...

Thought: 信息够了，生成诊断报告
Action:  调用 generate_diagnosis_report(...)
Final Answer: 📋 诊断报告...
```

### 定义工具

用 `@tool` 装饰器定义工具。Agent 通过工具的 `name` 和 `description` 来决定什么时候调用它：

```python
from langchain_core.tools import tool

@tool
def search_knowledge_base(query: str) -> str:
    """搜索设备知识库，查找设备手册、操作规范、故障案例等技术文档。
    当需要查询设备的技术参数、操作流程、日志规范、错误码含义、
    硬件接口说明等信息时使用此工具。

    Args:
        query: 搜索关键词，例如"制冰机故障"、"日志错误码"
    """
    results = search_with_scores(query, k=5)
    # ... 格式化返回
```

> description 写得好不好，直接影响 Agent 的智能程度。要写清楚"什么场景下该用这个工具"。

### 四个工具

| 工具 | 作用 | 数据来源 |
|------|------|----------|
| `query_device_status` | 查设备实时状态 | 模拟数据（后续接真实 API） |
| `fetch_device_logs` | 读取设备日志 | 本地文件 / SSH（可配置） |
| `search_knowledge_base` | 检索知识库 | ChromaDB 向量检索 |
| `generate_diagnosis_report` | 生成诊断报告 | 格式化输出 |

### 日志读取的双模式设计 (`log_reader.py`)

`fetch_device_logs` 支持两种读取模式，通过 `.env` 中的 `LOG_READ_MODE` 切换：

```bash
# .env
LOG_READ_MODE=local   # 同机部署，直接读本地文件
# LOG_READ_MODE=ssh   # 跨机部署，通过 SSH 远程读取
```

本地模式直接读文件，简单高效：

```python
def _read_local(log_type: str, lines: int, keyword: str) -> str:
    log_path = Path(LOG_PATHS[log_type])
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        all_lines = f.readlines()
    if keyword:
        all_lines = [l for l in all_lines if keyword.lower() in l.lower()]
    return "".join(all_lines[-lines:])
```

SSH 模式通过 subprocess 调用 ssh 命令远程读取：

```python
def _read_ssh(log_type: str, lines: int, keyword: str) -> str:
    remote_cmd = f"tail -n {lines} {LOG_PATHS[log_type]}"
    ssh_cmd = ["ssh", f"{settings.DEVICE_SSH_USER}@{settings.DEVICE_SSH_HOST}", remote_cmd]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
    return result.stdout
```

工具入口根据配置自动选择：

```python
@tool
def fetch_device_logs(log_type="syslog", lines=50, keyword="") -> str:
    if settings.LOG_READ_MODE == "local":
        return _read_local(log_type, lines, keyword)
    else:
        return _read_ssh(log_type, lines, keyword)
```

> 同机部署时用 `local` 模式：不需要 SSH 配置，读取更快，少一个故障点。

### 创建 Agent

用 LangGraph 的 `create_react_agent` 一行搞定：

```python
from langgraph.prebuilt import create_react_agent

TOOLS = [search_knowledge_base, fetch_device_logs, query_device_status, generate_diagnosis_report]

agent = create_react_agent(
    model=llm,                      # LLM 作为大脑
    tools=TOOLS,                    # 注册工具
    prompt=AGENT_SYSTEM_PROMPT,     # 系统提示词
)

# 执行
result = agent.invoke({
    "messages": [HumanMessage(content="制冰机报错 E03，怎么回事？")]
})
```

Agent 会自动完成：选择工具 → 填充参数 → 调用 → 解析结果 → 决定下一步 → 循环直到得出结论。

### 学到了什么

- Agent 和 Chain 的本质区别：固定流程 vs 动态决策
- ReAct 模式：Thought → Action → Observation 循环
- 工具定义：`@tool` 装饰器，description 是关键
- LangGraph：比 LangChain 的 AgentExecutor 更灵活的 Agent 编排框架

---

## Phase 4：生产化

> 目标：把 CLI 工具包装成可部署的 API 服务。

### FastAPI 服务

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SMYZE 设备故障诊断 Agent API")

# CORS 跨域（允许前端调用）
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```

### API 路由设计

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/chat` | 普通对话（非流式） |
| POST | `/api/chat/stream` | 普通对话（SSE 流式） |
| POST | `/api/diagnose` | Agent 诊断（工具调用） |
| POST | `/api/diagnose/stream` | Agent 诊断（SSE 流式） |
| POST | `/api/rag/query` | RAG 知识库检索 |
| GET | `/api/sessions` | 列出活跃会话 |
| DELETE | `/api/session/{id}` | 清除会话 |
| GET | `/health` | 健康检查 |

### SSE 流式输出

SSE（Server-Sent Events）是实现流式输出的标准方式，比 WebSocket 更轻量：

```python
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    session = _get_session(req.session_id, req.provider)

    async def event_generator():
        for token in session.stream_chat(req.message):
            # 每个 token 作为一个 SSE event 发送
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

前端用 `EventSource` API 接收：

```javascript
const source = new EventSource('/api/chat/stream');
source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.token) appendToChat(data.token);
    if (data.done) source.close();
};
```

### Agent 诊断接口

最核心的接口 —— 调用 Agent 执行完整诊断流程：

```python
@router.post("/diagnose")
async def diagnose(req: DiagnoseRequest):
    agent = create_diagnostic_agent(req.provider)
    result = agent.invoke({
        "messages": [HumanMessage(content=req.question)],
    })

    # 提取推理步骤和使用的工具
    tools_used = []
    steps = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tools_used.append(tc["name"])
                steps.append({"type": "tool_call", "tool": tc["name"], "args": tc["args"]})

    return DiagnoseResponse(result=final_content, tools_used=tools_used, steps=steps)
```

### Docker 部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y openssh-client  # SSH 客户端
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY scripts/ scripts/
COPY knowledge-base/ knowledge-base/
EXPOSE 8000
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 一键启动
docker-compose up -d

# 测试
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"question": "制冰机报错 E03"}'
```

### 学到了什么

- FastAPI：自动生成 Swagger 文档，Pydantic 数据校验
- SSE 流式输出：比 WebSocket 更适合"AI 逐字输出"的场景
- 会话管理：通过 session_id 维护多轮对话
- Docker 部署：Dockerfile + docker-compose 一键部署

---

## 整体数据流

把四个 Phase 串起来，看一次完整的诊断请求是怎么走的：

```
用户: "制冰机报错 E03，怎么处理？"
  │
  ▼
FastAPI 接收请求 (routes.py)
  │
  ▼
创建 ReAct Agent (diagnostic_agent.py)
  │  ├── LLM: Claude/GPT (client.py)
  │  └── Tools: 4 个工具
  │
  ▼
Agent 开始推理循环:
  │
  ├── Thought: 先查设备状态
  │   └── Action: query_device_status("BAR-001")
  │       └── 返回: 制冰机 error, E03
  │
  ├── Thought: 查日志看详情
  │   └── Action: fetch_device_logs("middleware", keyword="E03")
  │       └── SSH → 设备 → 返回日志
  │
  ├── Thought: 查知识库找解决方案
  │   └── Action: search_knowledge_base("制冰机 E03")
  │       └── ChromaDB 向量检索 → 返回相关文档
  │
  ├── Thought: 信息够了，生成报告
  │   └── Action: generate_diagnosis_report(...)
  │       └── 返回结构化报告
  │
  └── Final Answer: 📋 诊断报告
      │
      ▼
  FastAPI 返回 JSON 响应
```

---

## 踩过的坑

### 1. 代理冲突
国内开发经常开 Clash 等代理，但调用中转站 API 时代理会导致 SSL 错误。解决方案：在 `settings.py` 统一清除代理环境变量。

### 2. Extended Thinking 格式
Claude 的 extended thinking 模式下，`response.content` 不是字符串而是列表。需要 `extract_text()` 函数做兼容处理。

### 3. 流式输出降级
流式输出可能因为模型配置问题失败，所以做了降级逻辑：流式失败 → 自动切换为非流式调用。

### 4. 工具 description 的重要性
Agent 选择工具完全依赖 description。一开始写得太简单，Agent 经常选错工具。后来把"什么场景下该用"写清楚，效果好了很多。

---

## 快速上手

```bash
# 1. 克隆项目
git clone https://github.com/jacksonwangwbyy/ai-diagnostic-agent.git
cd ai-diagnostic-agent

# 2. 创建虚拟环境
python -m venv .venv
.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # Mac/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API Key

# 5. 构建知识库
python scripts/build_knowledge_base.py --local

# 6. 启动 CLI
python -m src.main

# 7. 或者启动 API 服务
uvicorn src.api.app:app --reload --port 8000
# 访问 http://localhost:8000/docs 查看 Swagger 文档
```

---

## 下一步可以做什么

- 接入真实设备 API（替换 `device_status.py` 的模拟数据）
- 添加更多工具（重启设备、推送固件更新等）
- 前端界面（React/Vue + SSE 流式展示）
- 对话记忆持久化（Redis 替代内存存储）
- 多 Agent 协作（诊断 Agent + 修复 Agent + 监控 Agent）
- 评估体系（自动评测 Agent 的诊断准确率）
