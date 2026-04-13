"""测试：会话管理（MemorySessionStore + 序列化/反序列化）"""
import json
from unittest.mock import patch, MagicMock
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.utils.session_store import (
    _serialize_session,
    _deserialize_session,
    MemorySessionStore,
    create_session_store,
)


class TestSerializeSession:

    def test_serialize_roundtrip(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            from src.llm.client import DiagnosticChat
            chat = DiagnosticChat("claude")
            chat.history.append(HumanMessage(content="你好"))
            chat.history.append(AIMessage(content="你好！"))
            raw = _serialize_session(chat)
            data = json.loads(raw)
            assert data["provider"] == "claude"
            assert len(data["messages"]) == 3

    def test_deserialize_new_format(self, mock_llm):
        raw = json.dumps({
            "provider": "openai",
            "messages": [
                {"type": "system", "content": "系统提示"},
                {"type": "human", "content": "你好"},
            ]
        })
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = _deserialize_session(raw, "claude")
            assert len(chat.history) == 2
            assert isinstance(chat.history[0], SystemMessage)
            assert isinstance(chat.history[1], HumanMessage)

    def test_deserialize_legacy_format(self, mock_llm):
        raw = json.dumps([
            {"type": "system", "content": "旧系统提示"},
            {"type": "human", "content": "旧消息"},
        ])
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = _deserialize_session(raw, "claude")
            assert len(chat.history) == 2


class TestMemorySessionStore:

    def test_get_creates_new_session(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            store = MemorySessionStore()
            chat = store.get("session-1", "claude")
            assert chat is not None
            assert chat.provider_name == "claude"

    def test_get_returns_same_session(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            store = MemorySessionStore()
            chat1 = store.get("session-1", "claude")
            chat2 = store.get("session-1", "claude")
            assert chat1 is chat2

    def test_delete_existing(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            store = MemorySessionStore()
            store.get("session-1", "claude")
            assert store.delete("session-1") is True
            assert store.delete("session-1") is False

    def test_list_sessions(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            store = MemorySessionStore()
            store.get("s1", "claude")
            store.get("s2", "openai")
            sessions = store.list_sessions()
            assert len(sessions) == 2
            ids = {s["id"] for s in sessions}
            assert ids == {"s1", "s2"}


class TestCreateSessionStore:

    def test_fallback_to_memory_no_url(self):
        with patch("src.utils.session_store.settings") as mock_settings:
            mock_settings.REDIS_URL = ""
            store = create_session_store()
            assert isinstance(store, MemorySessionStore)

    def test_redis_connection_failure(self):
        with patch("src.utils.session_store.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            with patch("src.utils.session_store.RedisSessionStore", side_effect=Exception("Connection refused")):
                store = create_session_store()
                assert isinstance(store, MemorySessionStore)
