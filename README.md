# 🤖 智能设备故障诊断 Agent

> SMYZE 饮吧设备 AI 故障诊断系统 | Java 工程师 → AI 工程师转型实战项目

## 项目简介

基于 LangChain + FastAPI 构建的智能设备故障诊断系统。接入 Claude/OpenAI 双模型，通过 RAG 检索设备手册和历史故障案例，Agent 自主调用日志读取、设备状态查询等工具，实现多步推理的故障根因分析。

## 技术栈

- **Python 3.11+** / **LangChain** / **FastAPI**
- **Claude API** + **OpenAI API**（多模型切换）
- **ChromaDB**（开发）→ **Milvus**（生产）
- **Docker** 容器化部署

## 项目结构

```
ai-diagnostic-agent/
├── src/                           # 源代码
│   ├── config/                    # 配置管理（API keys、模型参数）
│   ├── llm/                       # LLM 接入层（多模型管理）
│   ├── rag/                       # RAG 模块（文档加载、切分、检索）
│   ├── agent/                     # Agent 模块（工具编排、推理链）
│   ├── tools/                     # 工具实现（SSH日志、设备查询等）
│   ├── api/                       # FastAPI 接口层
│   └── utils/                     # 工具函数
├── knowledge-base/                # 知识库原始文档
│   ├── device-manuals/            # 设备手册（PDF/MD）
│   └── fault-cases/               # 历史故障案例
├── tests/                         # 测试
├── scripts/                       # 脚本（知识库构建等）
├── docs/                          # 文档 & 学习笔记
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python 依赖
└── docker-compose.yml             # Docker 部署
```

---

## 学习路线图

### 🟡 当前位置

- ✅ Java 后端 3 年（Spring Boot 3.x / Java 21 / 微服务）
- ✅ Python 实战经验（FastAPI 中间件、Socket.IO 服务）
- ✅ 真实 IoT 设备系统和数据源（SSH 可达）
- ✅ Claude / OpenAI API key
- ❌ RAG / Agent / Function Calling / 向量数据库 / LangChain

### 🎯 目标位置

具备 AI 应用工程师岗位核心竞争力，简历新增完整 AI 实战项目。

---

### Phase 1 — LLM 基础接入

> 理解 LLM API 调用原理，用 LangChain 完成基础对话

- [ ] LangChain 核心概念（Chain、Prompt Template、Output Parser）
- [ ] 接入 Claude API（langchain-anthropic）
- [ ] 接入 OpenAI API（langchain-openai）
- [ ] 多模型切换机制（通过配置切换 provider）
- [ ] Prompt Engineering（角色设定、Few-shot、CoT）
- [ ] 流式输出（Streaming）
- [ ] 多轮对话（对话历史管理）

**交付**：一个支持多模型切换的设备故障诊断对话 CLI

---

### Phase 2 — RAG 知识库

> 构建设备手册 + 历史故障案例知识库，实现检索增强问答

- [ ] 文档加载器（PDF、Markdown、文本）
- [ ] 文本切分策略（chunk_size / overlap / 语义切分）
- [ ] Embedding 模型选型与使用
- [ ] ChromaDB 向量存储与相似度检索
- [ ] 检索质量优化（Top-K、Reranking、元数据过滤）
- [ ] RAG 评估（检索准确率、回答质量）
- [ ] 导入真实设备文档到知识库

**交付**：输入故障问题 → 检索相关文档 → 生成带引用的回答

---

### Phase 3 — Agent & Function Calling

> 构建能自主调用工具、多步推理的诊断 Agent

- [ ] Function Calling / Tool Use 机制
- [ ] 工具定义与注册（@tool）
- [ ] 实现 fetch_device_logs（SSH 读取真实日志）
- [ ] 实现 query_device_status（调用 bar-deploy 接口）
- [ ] 实现 search_knowledge_base（RAG 检索）
- [ ] 实现 generate_diagnosis_report（结构化报告）
- [ ] ReAct 推理模式（Thought → Action → Observation）
- [ ] 多工具协作编排
- [ ] Agent 执行过程可视化

**交付**：输入故障描述 → Agent 自主推理 → 调用工具 → 输出诊断报告

---

### Phase 4 — 生产化

> 包装为可部署的服务，体现工程化能力

- [ ] FastAPI 服务化（REST + WebSocket）
- [ ] ChromaDB → Milvus 迁移
- [ ] 多模型负载与降级策略
- [ ] 对话历史持久化
- [ ] 流式输出（SSE）
- [ ] Docker 容器化部署
- [ ] API 文档（Swagger）

**交付**：完整可部署的 AI 诊断服务

---

## 快速开始

```bash
# 1. 克隆项目
cd "D:/software project/ai-diagnostic-agent"

# 2. 创建虚拟环境
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API keys

# 5. 开始 Phase 1
# （后续每个 Phase 会有具体的运行说明）
```

## 数据源

- 设备日志：`ssh smyze@192.168.42.1`（真实饮吧设备主机）
- 设备手册：`knowledge-base/device-manuals/`
- 故障案例：`knowledge-base/fault-cases/`
