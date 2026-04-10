"""
会话管理 - 支持内存和 Redis 两种存储后端

学习要点：
1. Redis 作为会话存储 —— 服务重启不丢失对话历史，多实例可共享
2. 序列化/反序列化 —— LangChain 的消息对象需要转成 JSON 存入 Redis
3. TTL 过期 —— 自动清理长期不活跃的会话，避免内存泄漏
4. 降级策略 —— Redis 不可用时自动降级到内存存储
"""
import json
import logging
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.config.settings import settings
from src.llm.client import DiagnosticChat, DIAGNOSTIC_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# 消息类型映射
MSG_TYPE_MAP = {
    "system": SystemMessage,
    "human": HumanMessage,
    "ai": AIMessage,
}


def _serialize_messages(messages: list) -> str:
    """将消息列表序列化为 JSON 字符串"""
    data = []
    for msg in messages:
        msg_type = type(msg).__name__.lower().replace("message", "")
        data.append({"type": msg_type, "content": msg.content})
    return json.dumps(data, ensure_ascii=False)


def _deserialize_messages(raw: str) -> list:
    """从 JSON 字符串反序列化为消息列表"""
    data = json.loads(raw)
    messages = []
    for item in data:
        cls = MSG_TYPE_MAP.get(item["type"])
        if cls:
            messages.append(cls(content=item["content"]))
    return messages


class MemorySessionStore:
    """内存会话存储（开发用 / Redis 不可用时的降级方案）"""

    def __init__(self):
        self._sessions: dict[str, DiagnosticChat] = {}

    def get(self, session_id: str, provider: str) -> DiagnosticChat:
        if session_id not in self._sessions:
            self._sessions[session_id] = DiagnosticChat(provider)
        return self._sessions[session_id]

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[dict]:
        return [
            {"id": sid, "provider": s.provider_name, "history_count": len(s.history)}
            for sid, s in self._sessions.items()
        ]


class RedisSessionStore:
    """Redis 会话存储（生产用）"""

    def __init__(self):
        import redis
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self._ttl = settings.SESSION_TTL
        self._prefix = "agent:session:"
        # 内存缓存（避免每次都反序列化）
        self._cache: dict[str, DiagnosticChat] = {}

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"

    def get(self, session_id: str, provider: str) -> DiagnosticChat:
        # 先查内存缓存
        if session_id in self._cache:
            return self._cache[session_id]

        # 再查 Redis
        key = self._key(session_id)
        raw = self._redis.get(key)

        if raw:
            chat = DiagnosticChat(provider)
            chat.history = _deserialize_messages(raw)
            self._cache[session_id] = chat
            return chat

        # 新建会话
        chat = DiagnosticChat(provider)
        self._save(session_id, chat)
        self._cache[session_id] = chat
        return chat

    def _save(self, session_id: str, chat: DiagnosticChat):
        """保存会话到 Redis"""
        key = self._key(session_id)
        raw = _serialize_messages(chat.history)
        self._redis.setex(key, self._ttl, raw)

    def save(self, session_id: str):
        """外部调用：保存指定会话"""
        if session_id in self._cache:
            self._save(session_id, self._cache[session_id])

    def delete(self, session_id: str) -> bool:
        self._cache.pop(session_id, None)
        return bool(self._redis.delete(self._key(session_id)))

    def list_sessions(self) -> list[dict]:
        keys = self._redis.keys(f"{self._prefix}*")
        sessions = []
        for key in keys:
            sid = key.replace(self._prefix, "")
            raw = self._redis.get(key)
            count = len(json.loads(raw)) if raw else 0
            sessions.append({"id": sid, "history_count": count})
        return sessions


def create_session_store():
    """
    创建会话存储实例

    优先使用 Redis，连接失败自动降级到内存存储。
    """
    if settings.REDIS_URL:
        try:
            store = RedisSessionStore()
            store._redis.ping()
            logger.info(f"使用 Redis 会话存储: {settings.REDIS_URL}")
            return store
        except Exception as e:
            logger.warning(f"Redis 连接失败 ({e})，降级到内存存储")

    logger.info("使用内存会话存储")
    return MemorySessionStore()
