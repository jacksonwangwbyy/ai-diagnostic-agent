# 🤖 智能设备故障诊断 Agent

> SMYZE 饮吧设备 AI 故障诊断系统 | Java 工程师 → AI 工程师转型实战项目

## 项目简介

基于 LangChain + FastAPI 构建的智能设备故障诊断系统。接入 Claude/OpenAI 双模型，通过 RAG 检索设备手册和历史故障案例，Agent 自主调用日志读取、设备状态查询等工具，实现多步推理的故障根因分析。

## 技术栈

- **Python 3.11+** / **LangChain** / **FastAPI**
- **Claude API** + **OpenAI API**（多模型切换，通过中转站代理）
- **ChromaDB**（开发）→ **Milvus**（生产）
- **HuggingFace Embedding**（本地）/ **OpenAI Embedding**（API）
- **Docker** 容器化部署

## 项目结构

```
ai-diagnostic-agent/
├── src/                           # 源代码
│   ├── config/                    # 配置管理
│   │   └── settings.py            # .env 加载 & Settings 类
│   ├── llm/                       # LLM 接入层
│   │   └── client.py              # 多模型客户端 + DiagnosticChat
│   ├── rag/                       # RAG 模块
│   │   ├── loader.py              # 文档加载器（MD/PDF/TXT）
│   │   ├── splitter.py            # 文本切分（标题切分+字符切分）
│   │   ├── vectorstore.py         # ChromaDB 向量存储与检索
│   │   ├── reranker.py            # CrossEncoder 重排序
│   │   ├── hybrid_search.py       # BM25 混合检索 + RRF 融合
│   │   └── chain.py               # RAG 检索链（混合检索+生成+引用）
│   ├── agent/                     # Agent 模块
│   │   ├── diagnostic_agent.py    # ReAct 诊断 Agent（6 工具）
│   │   ├── repair_agent.py        # 维修建议 Agent
│   │   ├── monitor_agent.py       # 设备监控 Agent
│   │   └── supervisor.py          # Supervisor 多 Agent 编排引擎
│   ├── tools/                     # 工具实现
│   │   ├── knowledge_search.py    # 知识库检索工具（混合检索+重排序）
│   │   ├── log_reader.py          # 设备日志读取工具（local/ssh 双模式）
│   │   ├── device_status.py       # 设备状态查询工具（对接 bar_middleware 真实 API）
│   │   ├── diagnosis_report.py    # 诊断报告生成工具
│   │   ├── device_restart.py      # 设备服务重启工具（SSH 命令白名单）
│   │   └── firmware_check.py      # 固件版本检查工具
│   ├── api/                       # FastAPI 接口
│   │   ├── app.py                 # FastAPI 应用入口
│   │   ├── limiter.py             # API 限流（slowapi）
│   │   ├── models.py              # 请求/响应数据模型
│   │   └── routes.py              # API 路由（REST + SSE）
│   ├── utils/                     # 工具函数
│   └── main.py                    # CLI 入口
├── knowledge-base/                # 知识库原始文档
│   ├── device-manuals/            # 设备手册（14 个文档）
│   └── fault-cases/               # 历史故障案例
├── scripts/
│   └── build_knowledge_base.py    # 一键构建知识库脚本
├── tests/                         # 测试（133 用例）
├── evaluation/                    # RAG 评估框架
│   ├── eval_dataset.json          # 20 组 Q&A 评估数据集
│   ├── run_eval.py                # 自动评估脚本
│   └── README.md                  # 评估使用说明
├── docs/                          # 文档 & 学习笔记
├── frontend/                      # React 前端（Vite + TypeScript + SSE）
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python 依赖
├── Dockerfile                     # 后端容器化
├── docker-compose.yml             # Agent + Milvus 部署
└── .gitignore
```

---

## 学习路线图

### 🟡 当前位置

- ✅ Java 后端 3 年（Spring Boot 3.x / Java 21 / 微服务）
- ✅ Python 实战经验（FastAPI 中间件、Socket.IO 服务）
- ✅ 真实 IoT 设备系统和数据源（SSH 可达）
- ✅ Claude / OpenAI API key（通过中转站）
- 🔄 正在学习 RAG / Agent / Function Calling / 向量数据库 / LangChain

### 🎯 目标位置

具备 AI 应用工程师岗位核心竞争力，简历新增完整 AI 实战项目。

---

### Phase 1 — LLM 基础接入 ✅

> 理解 LLM API 调用原理，用 LangChain 完成基础对话

- [x] LangChain 核心概念（ChatModel、消息类型）
- [x] 接入 Claude API（langchain-anthropic + 中转站）
- [x] 接入 OpenAI API（langchain-openai + 中转站）
- [x] 多模型切换机制（通过配置切换 provider）
- [x] Prompt Engineering（设备故障诊断系统提示词）
- [x] 流式输出（Streaming + extended thinking 兼容）
- [x] 多轮对话（对话历史管理）

**交付**：CLI 对话工具 `python -m src.main`，支持 `/switch`、`/clear` 命令

---

### Phase 2 — RAG 知识库 ✅

> 构建设备手册 + 历史故障案例知识库，实现检索增强问答

- [x] 文档加载器（Markdown、PDF、TXT）
- [x] 文本切分策略（Markdown 标题切分 + 递归字符切分，chunk_size=800）
- [x] Embedding 模型（HuggingFace 本地 all-MiniLM-L6-v2 + OpenAI API 可选）
- [x] ChromaDB 向量存储与相似度检索
- [x] 导入 14 个真实设备文档 → 434 个文档块
- [x] RAG 问答链（检索 + Prompt 拼接 + LLM 生成 + 引用溯源）
- [x] 检索质量优化（CrossEncoder Reranking + BM25 混合检索 + RRF 融合）
- [x] RAG 评估体系（Recall@K、MRR、回答质量自动评估）

**交付**：一键构建知识库 `python scripts/build_knowledge_base.py --local`

---

### Phase 3 — Agent & Function Calling ✅

> 构建能自主调用工具、多步推理的诊断 Agent

- [x] Function Calling / Tool Use 机制（LangGraph ReAct Agent）
- [x] 工具定义与注册（@tool 装饰器）
- [x] 实现 fetch_device_logs（SSH 读取真实日志）
- [x] 实现 query_device_status（设备状态查询，含模拟数据）
- [x] 实现 search_knowledge_base（RAG 检索）
- [x] 实现 generate_diagnosis_report（结构化报告）
- [x] ReAct 推理模式（LangGraph create_react_agent）
- [x] 多工具协作编排（6 工具自主调度）
- [x] Agent 执行过程可视化（CLI verbose 模式）
- [x] 设备服务重启工具（SSH 命令白名单）
- [x] 固件版本检查工具（API 查询）
- [x] 多 Agent 协作系统（Supervisor + 诊断/维修/监控 Agent）

**交付**：`python -m src.main` Agent 模式，支持 `/agent` 和 `/chat` 切换

---

### Phase 4 — 生产化 ✅

> 包装为可部署的服务，体现工程化能力

- [x] FastAPI 服务化（REST + SSE 流式）
- [x] API 端点：对话、Agent 诊断、RAG 检索、会话管理
- [x] 流式输出（SSE，Server-Sent Events）
- [x] API 文档（Swagger，访问 /docs）
- [x] Docker 容器化（Dockerfile + docker-compose.yml）
- [x] Milvus 集成（docker-compose 中配置）
- [x] ChromaDB → Milvus 迁移（向量存储切换）
- [x] 多模型降级策略（provider A 失败自动切 B）
- [x] 对话历史持久化（Redis，自动降级到内存）
- [x] React 前端（Vite + TypeScript + SSE 流式，含模型选择/多Agent开关/报告导出/错误重试）
- [x] API 限流（slowapi，按端点分级限制）
- [x] 部署文档（deployment-guide.md + api-guide.md）

**交付**：`uvicorn src.api.app:app` 或 `docker compose up`

---

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/jacksonwangwbyy/ai-diagnostic-agent.git
cd ai-diagnostic-agent

# 2. 创建虚拟环境
python -m venv .venv
.venv/Scripts/activate      # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API keys 和中转站地址

# 5. 构建知识库
python scripts/build_knowledge_base.py --local

# 6a. CLI 模式（Agent 对话）
python -m src.main

# 6b. API 服务模式
uvicorn src.api.app:app --reload --port 8000
# 访问 http://localhost:8000/docs 查看 Swagger 文档

# 6c. 前端开发模式
cd frontend && npm install && npm run dev
# 访问 http://localhost:3000（自动代理到后端 8000）

# 6d. Docker 部署（含 Milvus + Redis）
docker compose up -d
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 普通对话（非流式） |
| POST | `/api/chat/stream` | 普通对话（SSE 流式） |
| POST | `/api/diagnose` | Agent 故障诊断 |
| POST | `/api/diagnose/stream` | Agent 诊断（SSE 流式） |
| POST | `/api/rag/query` | RAG 知识库检索 |
| GET | `/api/sessions` | 列出活跃会话 |
| DELETE | `/api/session/{id}` | 清除会话 |
| GET | `/health` | 健康检查 |
| GET | `/docs` | Swagger 文档 |

## 数据源

- 设备日志：`ssh smyze@192.168.42.1`（真实饮吧设备主机）
- 设备手册：`knowledge-base/device-manuals/`（14 个文档）
- 故障案例：`knowledge-base/fault-cases/`
