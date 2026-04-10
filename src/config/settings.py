"""配置管理 - 从 .env 加载所有配置"""
import os
from dotenv import load_dotenv

load_dotenv()

# 统一清除系统代理，避免 Clash 等代理与中转站 SSL 冲突
# 只在这里做一次，其他模块不再重复
for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(key, None)
os.environ["NO_PROXY"] = "*"


class Settings:
    # LLM API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # API Base URLs (中转站)
    ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")

    # Model Config
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "claude")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # 日志读取模式: "local"（本地文件）或 "ssh"（远程 SSH）
    LOG_READ_MODE: str = os.getenv("LOG_READ_MODE", "local")

    # SSH（仅 LOG_READ_MODE=ssh 时使用）
    DEVICE_SSH_HOST: str = os.getenv("DEVICE_SSH_HOST", "192.168.42.1")
    DEVICE_SSH_USER: str = os.getenv("DEVICE_SSH_USER", "smyze")
    DEVICE_SSH_KEY_PATH: str = os.getenv("DEVICE_SSH_KEY_PATH", "~/.ssh/id_rsa")

    # Vector DB
    VECTOR_DB_TYPE: str = os.getenv("VECTOR_DB_TYPE", "chromadb")
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

    # Bar Middleware（同机部署，默认 localhost:8003）
    MIDDLEWARE_BASE_URL: str = os.getenv("MIDDLEWARE_BASE_URL", "http://localhost:8003")

    # Bar Deploy Server
    BAR_DEPLOY_SERVER_URL: str = os.getenv("BAR_DEPLOY_SERVER_URL", "http://localhost:8080")


settings = Settings()
