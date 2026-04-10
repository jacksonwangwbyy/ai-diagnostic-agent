"""
LLM 客户端 - 支持 Claude / OpenAI 多模型切换 + 自动降级

学习要点：
1. LangChain 的 ChatModel 抽象 - 统一接口，不同实现
2. ChatAnthropic / ChatOpenAI - 两个 provider 的接入方式
3. base_url 配置 - 支持中转站/代理
4. 流式输出 - stream() 方法
5. 多轮对话 - 消息历史管理
6. with_fallbacks() - 主模型失败时自动切换到备用模型
"""
import logging
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.config.settings import settings

logger = logging.getLogger(__name__)

# provider 名称 → 构造函数映射
PROVIDERS = {"claude", "openai"}


def _create_single_llm(provider: str):
    """创建单个 provider 的 LLM 实例（内部使用）"""
    if provider == "claude":
        kwargs = {
            "model": settings.CLAUDE_MODEL,
            "api_key": settings.ANTHROPIC_API_KEY,
            "max_tokens": 4096,
        }
        if settings.ANTHROPIC_BASE_URL:
            kwargs["base_url"] = settings.ANTHROPIC_BASE_URL
        return ChatAnthropic(**kwargs)

    elif provider == "openai":
        kwargs = {
            "model": settings.OPENAI_MODEL,
            "api_key": settings.OPENAI_API_KEY,
        }
        if settings.OPENAI_BASE_URL:
            kwargs["base_url"] = settings.OPENAI_BASE_URL
        return ChatOpenAI(**kwargs)

    else:
        raise ValueError(f"不支持的 provider: {provider}，请使用 'claude' 或 'openai'")


def _get_fallback_provider(provider: str) -> str | None:
    """获取备用 provider（claude ↔ openai）"""
    fallback_map = {"claude": "openai", "openai": "claude"}
    fallback = fallback_map.get(provider)
    # 检查备用 provider 是否配置了 API key
    if fallback == "claude" and not settings.ANTHROPIC_API_KEY:
        return None
    if fallback == "openai" and not settings.OPENAI_API_KEY:
        return None
    return fallback


def create_llm(provider: str = None):
    """
    创建 LLM 实例（支持自动降级）

    当 LLM_FALLBACK_ENABLED=true 且备用 provider 有 API key 时，
    主 provider 调用失败会自动切换到备用 provider。

    Args:
        provider: "claude" 或 "openai"，默认读取配置

    Returns:
        ChatModel 实例（可能带 fallback 包装）
    """
    provider = provider or settings.DEFAULT_LLM_PROVIDER
    primary = _create_single_llm(provider)

    if not settings.LLM_FALLBACK_ENABLED:
        return primary

    fallback_provider = _get_fallback_provider(provider)
    if not fallback_provider:
        return primary

    fallback = _create_single_llm(fallback_provider)
    logger.info(f"LLM 降级链: {provider} → {fallback_provider}")
    return primary.with_fallbacks([fallback])


def extract_text(content) -> str:
    """
    从 LLM 返回内容中提取纯文本。

    有些中转站/模型会返回 extended thinking 格式（content 是 list），
    需要从中提取 type='text' 的部分。
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text"]
        return "".join(parts).strip()
    return str(content)


# 设备故障诊断的系统提示词
DIAGNOSTIC_SYSTEM_PROMPT = """你是 SMYZE 饮吧设备的智能故障诊断助手。

你的职责：
1. 分析设备故障现象，定位根因
2. 提供具体的排查步骤和修复建议
3. 参考设备手册和历史故障案例给出专业判断

你的风格：
- 专业但易懂，像一个经验丰富的运维工程师在和同事交流
- 先问清楚故障现象，再给出分析
- 给出的建议要具体可执行，不要泛泛而谈

设备类型包括：饮品制作机、制冰机、冷藏柜、点餐屏、网络设备等。
"""


class DiagnosticChat:
    """
    设备故障诊断对话管理器

    学习要点：
    - 消息类型：SystemMessage / HumanMessage / AIMessage
    - 对话历史：通过维护消息列表实现多轮对话
    - 流式输出：stream() 逐 token 返回
    """

    def __init__(self, provider: str = None):
        self.llm = create_llm(provider)
        self.history: list = [SystemMessage(content=DIAGNOSTIC_SYSTEM_PROMPT)]
        self.provider_name = provider or settings.DEFAULT_LLM_PROVIDER

    def chat(self, user_input: str) -> str:
        """单次对话（非流式）"""
        self.history.append(HumanMessage(content=user_input))
        response = self.llm.invoke(self.history)
        text = extract_text(response.content)
        self.history.append(AIMessage(content=text))
        return text

    def stream_chat(self, user_input: str):
        """
        流式对话 - 逐 token 输出

        注意：extended thinking 模式下流式输出可能返回复杂格式，
        这里做了兜底：如果流式失败，降级为非流式调用。
        """
        self.history.append(HumanMessage(content=user_input))
        full_response = ""
        used_fallback = False

        try:
            for chunk in self.llm.stream(self.history):
                token = chunk.content
                if isinstance(token, str):
                    full_response += token
                    yield token
                elif isinstance(token, list):
                    # extended thinking 流式块
                    for block in token:
                        if isinstance(block, dict) and block.get("type") == "text":
                            full_response += block["text"]
                            yield block["text"]
        except Exception:
            # 流式失败，降级为非流式
            if not full_response:
                # 移除已添加的 HumanMessage，用 chat 方法重试
                self.history.pop()
                result = self.chat(user_input)
                yield result
                used_fallback = True

        if not used_fallback:
            text = full_response.strip()
            self.history.append(AIMessage(content=text))

    def clear_history(self):
        """清空对话历史，保留系统提示词"""
        self.history = [SystemMessage(content=DIAGNOSTIC_SYSTEM_PROMPT)]

    def switch_model(self, provider: str):
        """切换模型 provider"""
        self.llm = create_llm(provider)
        self.provider_name = provider
        print(f"已切换到 {provider} 模型")
