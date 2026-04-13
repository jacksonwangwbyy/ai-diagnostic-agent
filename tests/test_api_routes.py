"""测试：API 路由（集成测试，使用 FastAPI TestClient）"""
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from src.api.app import app
from src.utils.session_store import MemorySessionStore


@pytest.fixture
def mock_store(mock_llm):
    """Mock 会话存储"""
    with patch("src.llm.client.create_llm", return_value=mock_llm):
        store = MemorySessionStore()
        with patch("src.api.routes._store", store):
            yield store


@pytest_asyncio.fixture
async def client():
    """异步测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

class TestChatEndpoint:

    @pytest.mark.asyncio
    async def test_chat_success(self, client, mock_store):
        response = await client.post("/api/chat", json={
            "message": "你好",
            "provider": "claude",
            "session_id": "test-session",
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_chat_missing_message(self, client):
        response = await client.post("/api/chat", json={"provider": "claude"})
        assert response.status_code == 422


class TestRAGEndpoint:

    @pytest.mark.asyncio
    async def test_rag_query(self, client):
        mock_result = {"answer": "测试回答", "sources": ["doc1.md"], "context_count": 1}
        with patch("src.api.routes.rag_query", return_value=mock_result):
            response = await client.post("/api/rag/query", json={"query": "制冰机故障", "top_k": 3})
            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "测试回答"


class TestSessionEndpoints:

    @pytest.mark.asyncio
    async def test_list_sessions(self, client, mock_store):
        response = await client.get("/api/sessions")
        assert response.status_code == 200
        assert "sessions" in response.json()

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, client, mock_store):
        response = await client.delete("/api/session/nonexistent")
        assert response.status_code == 200
        assert "不存在" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_delete_session_exists(self, client, mock_store):
        await client.post("/api/chat", json={"message": "创建会话", "session_id": "to-delete"})
        response = await client.delete("/api/session/to-delete")
        assert response.status_code == 200
        assert "已清除" in response.json()["message"]
