# 智能设备故障诊断 Agent — 设计文档

> 创建时间：2026-04-09
> 作者：王冰岩（Jackson）
> 目标：从 Java 工程师转型 AI 工程师的学习+实战项目

---

## 1. 项目定位

基于 LLM 的智能设备故障诊断系统，能够读取饮吧设备的真实日志，结合设备手册和历史故障案例知识库，自动分析故障原因并给出处理建议。

同时作为 AI 工程师核心技能的学习载体，覆盖：
- LLM API 集成（Function Calling）
- Agent 开发（工具调用、多步推理）
- RAG（检索增强生成）
- 向量数据库（ChromaDB → Milvus）
- Prompt Engineering

## 2. 技术栈

| 类别 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | AI 生态主力语言 |
| LLM 框架 | LangChain | 最主流的 LLM 编排框架 |
| Web 框架 | FastAPI | 已有经验，异步高性能 |
| 主力模型 | Claude API | 中文理解强，Function Calling 完善 |
| 备选模型 | OpenAI API | 生态最成熟，用于多模型切换 |
| 向量数据库（开发） | ChromaDB | 轻量，pip install 即用 |
| 向量数据库（生产） | Milvus | 生产级，简历认可度高 |
| 真实数据源 | SSH (192.168.42.1) | 饮吧设备真实日志和状态 |

## 3. 系统架构

```
用户（运维人员）
    │
    ▼
FastAPI Web 服务（对话接口 + REST API）
    │
    ▼
LangChain Agent（核心编排层）
    ├── LLM（Claude / OpenAI，多模型切换）
    ├── Tools（Agent 可调用的工具）
    │   ├── 日志检索工具 — SSH 读取真实设备日志
    │   ├── 设备状态查询工具 — 调用 bar-deploy 接口
    │   ├── 知识库检索工具 — RAG 检索设备手册/历史案例
    │   └── 故障报告生成工具 — 结构化输出诊断结果
    │
    ▼
RAG 知识库
    ├── 文档加载 & 切分（设备手册、故障案例）
    ├── Embedding 模型（向量化）
    └── ChromaDB / Milvus（向量存储 & 检索）
```

## 4. 学习阶段划分

### Phase 1 — LLM 基础接入
**目标**：理解 LLM API 调用原理，能用 LangChain 完成基础对话

学习内容：
- LangChain 核心概念（Chain、Prompt Template、Output Parser）
- Claude / OpenAI API 接入与调用
- 多模型切换机制
- Prompt Engineering 系统化方法（角色设定、Few-shot、CoT）
- 流式输出（Streaming）

交付物：
- 一个能和 Claude/OpenAI 对话的 CLI 工具
- 支持多模型切换
- 包含设备故障诊断的系统提示词

### Phase 2 — RAG 知识库
**目标**：构建设备手册和历史故障案例的知识库，实现基于检索的问答

学习内容：
- 文档加载器（PDF、Markdown、文本文件）
- 文本切分策略（chunk_size、chunk_overlap、按语义切分）
- Embedding 模型选型（OpenAI Embedding / 开源模型）
- ChromaDB 向量存储与相似度检索
- 检索质量优化（Top-K 调优、Reranking、混合检索）
- RAG 评估方法（检索准确率、回答质量）

交付物：
- 设备手册知识库（从现有 PDF/MD 文档导入）
- 历史故障案例库（从真实日志中提取）
- RAG 问答接口：输入问题 → 检索相关文档 → 生成回答

### Phase 3 — Agent & Function Calling
**目标**：构建能自主调用工具、多步推理的诊断 Agent

学习内容：
- Function Calling / Tool Use 机制
- LangChain Tools 定义与注册
- ReAct 推理模式（Thought → Action → Observation 循环）
- 多工具协作编排
- Agent 记忆与上下文管理

工具清单：
1. **fetch_device_logs** — SSH 到 192.168.42.1 读取指定设备的日志
2. **query_device_status** — 调用 bar-deploy 接口查询设备实时状态
3. **search_knowledge_base** — RAG 检索设备手册/历史故障案例
4. **generate_diagnosis_report** — 结构化输出故障诊断报告

交付物：
- 完整的诊断 Agent，能接收故障描述 → 自主决定调用哪些工具 → 多步推理 → 输出诊断结果
- Agent 执行过程可视化（展示推理链路）

### Phase 4 — 生产化
**目标**：将 Agent 包装为可部署的服务，具备生产级能力

学习内容：
- FastAPI 服务化（REST + WebSocket）
- ChromaDB → Milvus 迁移
- 多模型负载与降级策略
- 对话历史持久化
- 流式输出（SSE）
- Docker 容器化部署

交付物：
- 完整的 FastAPI 服务
- Milvus 向量数据库集成
- Docker Compose 一键部署
- API 文档（Swagger）

## 5. 项目目录结构

```
ai-diagnostic-agent/
├── docs/                          # 文档
│   ├── learning-notes/            # 每个 Phase 的学习笔记
│   └── superpowers/specs/         # 设计文档
├── knowledge-base/                # 知识库原始文档
│   ├── device-manuals/            # 设备手册
│   └── fault-cases/               # 历史故障案例
├── src/
│   ├── config/                    # 配置（API keys、模型参数）
│   ├── llm/                       # LLM 接入层（多模型管理）
│   ├── rag/                       # RAG 模块（文档加载、切分、检索）
│   ├── agent/                     # Agent 模块（工具定义、推理编排）
│   ├── tools/                     # 工具实现（SSH日志、设备查询等）
│   ├── api/                       # FastAPI 接口层
│   └── utils/                     # 工具函数
├── tests/                         # 测试
├── scripts/                       # 脚本（知识库构建、数据导入等）
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python 依赖
├── docker-compose.yml             # Docker 部署（Phase 4）
└── README.md                      # 项目说明
```

## 6. 现状与蓝图

### 现状（Phase 1 & 2 已完成）
- ✅ Java 后端开发 3 年，Spring Boot / 微服务 / DevOps 扎实
- ✅ Python 有实战经验（FastAPI 中间件、Socket.IO 服务）
- ✅ 有真实的 IoT 设备系统和数据源
- ✅ 有 Claude 和 OpenAI 的 API key（通过中转站）
- ✅ LangChain 核心概念掌握（ChatModel、消息类型、Prompt Template）
- ✅ Claude / OpenAI 双模型接入与切换
- ✅ 流式输出、多轮对话已实现
- ✅ RAG pipeline 已跑通（文档加载 → 切分 → Embedding → ChromaDB 检索 → 生成）
- ✅ 14 个真实设备文档已导入知识库（434 个文档块）
- 🔄 Agent 开发（Phase 3 进行中）
- ❌ 向量数据库迁移（Milvus）
- ❌ 生产化部署（FastAPI + Docker）

### 蓝图（完成后你的位置）
- ✅ 掌握 LangChain 框架，能独立开发 LLM 应用
- ✅ 掌握 RAG 全流程：文档处理 → Embedding → 向量检索 → 生成
- ✅ 掌握 Agent 开发：Function Calling、ReAct 推理、多工具编排
- ✅ 掌握向量数据库：ChromaDB（开发）+ Milvus（生产）
- ✅ 掌握系统化的 Prompt Engineering
- ✅ 有一个基于真实业务场景的 AI 项目可以写进简历
- ✅ 具备 AI 应用工程师岗位的核心竞争力

### 简历上可以这样写
> 基于 LangChain + FastAPI 构建智能设备故障诊断 Agent，集成 Claude/OpenAI 多模型，
> 通过 RAG 技术构建设备手册和历史故障案例知识库（ChromaDB/Milvus），
> 实现 Function Calling 驱动的多工具自主推理，支持实时日志分析、故障根因定位和处理建议生成。
