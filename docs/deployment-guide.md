# 部署最佳实践

## 环境要求

- Python 3.11+
- Docker & Docker Compose（生产部署）
- Redis（会话持久化，可选）
- 4GB+ RAM（含 HuggingFace Embedding 模型）

## 快速部署

### 开发环境

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
cp .env.example .env    # 填入 API keys
python scripts/build_knowledge_base.py --local
uvicorn src.api.app:app --reload --port 8000
```

### 生产环境（Docker）

```bash
cp .env.example .env    # 填入生产配置
docker compose up -d
# 服务启动后访问 http://localhost:8000/docs
```

`docker-compose.yml` 包含：Agent 服务 + Redis + Milvus

## 环境变量配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Claude API Key | 必填 |
| `OPENAI_API_KEY` | OpenAI API Key | 可选 |
| `ANTHROPIC_BASE_URL` | Claude 中转站地址 | 空（直连） |
| `OPENAI_BASE_URL` | OpenAI 中转站地址 | 空（直连） |
| `DEFAULT_LLM_PROVIDER` | 默认模型 | `claude` |
| `LOG_READ_MODE` | 日志读取模式 | `local` |
| `VECTOR_DB_TYPE` | 向量数据库 | `chromadb` |
| `REDIS_URL` | Redis 连接地址 | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | 允许的前端域名 | `http://localhost:3000,http://localhost:5173` |

## 知识库构建

```bash
# 本地 Embedding（推荐，无需 API）
python scripts/build_knowledge_base.py --local

# OpenAI Embedding（效果更好，需要 API key）
python scripts/build_knowledge_base.py
```

知识库文件放在 `knowledge-base/` 目录，支持 `.md`、`.pdf`、`.txt` 格式。

## 常见问题

**Q: 启动时报 `ModuleNotFoundError`**
```bash
pip install -r requirements.txt
```

**Q: 知识库检索无结果**
```bash
# 重新构建知识库
python scripts/build_knowledge_base.py --local
```

**Q: Redis 连接失败**

系统会自动降级到内存存储，不影响功能。生产环境建议配置 Redis 以持久化会话。

**Q: SSH 连接设备超时**

检查 `.env` 中的 `DEVICE_SSH_HOST`、`DEVICE_SSH_USER`、`DEVICE_SSH_KEY_PATH` 配置。
