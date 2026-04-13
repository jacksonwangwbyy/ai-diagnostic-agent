"""测试共享 fixtures"""
import os
import pytest
from unittest.mock import MagicMock, patch

# 在导入项目代码之前设置测试环境变量
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_BASE_URL", "")
os.environ.setdefault("OPENAI_BASE_URL", "")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "claude")
os.environ.setdefault("LOG_READ_MODE", "local")
os.environ.setdefault("VECTOR_DB_TYPE", "chromadb")
os.environ.setdefault("CHROMA_PERSIST_DIR", "./test_chroma_data")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("LLM_FALLBACK_ENABLED", "false")
os.environ.setdefault("MIDDLEWARE_BASE_URL", "http://localhost:8003")


@pytest.fixture
def mock_llm():
    """Mock LLM 实例，返回固定响应"""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="这是一个测试回复")
    llm.stream.return_value = [MagicMock(content="测试"), MagicMock(content="回复")]
    llm.with_fallbacks.return_value = llm
    return llm


@pytest.fixture
def sample_documents():
    """测试用文档列表"""
    from langchain_core.documents import Document
    return [
        Document(
            page_content="# 中间件说明\n\n## 概述\n\nbar_middleware 是饮吧设备的核心中间件。\n\n## 接口\n\n提供 RESTful API。",
            metadata={"source": "test.md", "filename": "test.md", "file_type": "markdown"},
        ),
        Document(
            page_content="制冰机操作手册，包含日常维护和故障排查步骤。",
            metadata={"source": "ice.txt", "filename": "ice.txt", "file_type": "text"},
        ),
    ]


@pytest.fixture
def tmp_log_file(tmp_path):
    """创建临时日志文件"""
    log_file = tmp_path / "test.log"
    log_file.write_text(
        "2024-01-01 INFO 系统启动\n"
        "2024-01-01 ERROR 连接失败\n"
        "2024-01-01 WARN 温度偏高\n"
        "2024-01-01 INFO 任务完成\n"
        "2024-01-01 ERROR 超时错误\n",
        encoding="utf-8",
    )
    return log_file


@pytest.fixture
def tmp_markdown_file(tmp_path):
    """创建临时 Markdown 文件"""
    md_file = tmp_path / "test_doc.md"
    md_file.write_text(
        "# 标题一\n\n内容一\n\n## 标题二\n\n内容二\n\n### 标题三\n\n内容三\n",
        encoding="utf-8",
    )
    return md_file
