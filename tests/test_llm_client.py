"""测试：LLM 客户端（多模型切换、降级、文本提取）"""
from unittest.mock import patch, MagicMock
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.llm.client import (
    _create_single_llm,
    _get_fallback_provider,
    create_llm,
    extract_text,
    DiagnosticChat,
)


class TestExtractText:
    """文本提取（处理 extended thinking 格式）"""

    def test_string_content(self):
        assert extract_text("hello") == "hello"

    def test_list_content_with_text_blocks(self):
        content = [
            {"type": "thinking", "text": "思考中..."},
            {"type": "text", "text": "最终回答"},
        ]
        assert extract_text(content) == "最终回答"

    def test_list_multiple_text_blocks(self):
        content = [{"type": "text", "text": "部分1"}, {"type": "text", "text": "部分2"}]
        assert extract_text(content) == "部分1部分2"

    def test_empty_list(self):
        assert extract_text([]) == ""

    def test_other_types(self):
        assert extract_text(123) == "123"


class TestCreateSingleLLM:
    """单 provider LLM 创建"""

    def test_create_claude(self):
        with patch("src.llm.client.ChatAnthropic") as mock_cls:
            _create_single_llm("claude")
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args[1]
            assert "api_key" in call_kwargs

    def test_create_openai(self):
        with patch("src.llm.client.ChatOpenAI") as mock_cls:
            _create_single_llm("openai")
            mock_cls.assert_called_once()

    def test_unsupported_provider(self):
        import pytest
        with pytest.raises(ValueError, match="不支持"):
            _create_single_llm("gemini")


class TestGetFallbackProvider:

    def test_claude_fallback_to_openai(self):
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "key"
            assert _get_fallback_provider("claude") == "openai"

    def test_openai_fallback_to_claude(self):
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "key"
            assert _get_fallback_provider("openai") == "claude"

    def test_no_fallback_without_key(self):
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            assert _get_fallback_provider("claude") is None


class TestCreateLLM:

    def test_no_fallback_when_disabled(self):
        with patch("src.llm.client._create_single_llm") as mock_create:
            mock_llm = MagicMock()
            mock_create.return_value = mock_llm
            with patch("src.llm.client.settings") as mock_settings:
                mock_settings.DEFAULT_LLM_PROVIDER = "claude"
                mock_settings.LLM_FALLBACK_ENABLED = False
                result = create_llm()
                assert result == mock_llm
                mock_llm.with_fallbacks.assert_not_called()

    def test_fallback_chain_when_enabled(self):
        primary = MagicMock()
        fallback = MagicMock()
        chained = MagicMock()
        primary.with_fallbacks.return_value = chained
        with patch("src.llm.client._create_single_llm", side_effect=[primary, fallback]):
            with patch("src.llm.client.settings") as mock_settings:
                mock_settings.DEFAULT_LLM_PROVIDER = "claude"
                mock_settings.LLM_FALLBACK_ENABLED = True
                with patch("src.llm.client._get_fallback_provider", return_value="openai"):
                    result = create_llm()
                    primary.with_fallbacks.assert_called_once_with([fallback])
                    assert result == chained


class TestDiagnosticChat:

    def test_init(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = DiagnosticChat("claude")
            assert len(chat.history) == 1
            assert isinstance(chat.history[0], SystemMessage)
            assert chat.provider_name == "claude"

    def test_chat(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = DiagnosticChat("claude")
            result = chat.chat("你好")
            assert result == "这是一个测试回复"
            assert len(chat.history) == 3
            assert isinstance(chat.history[1], HumanMessage)
            assert isinstance(chat.history[2], AIMessage)

    def test_clear_history(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = DiagnosticChat("claude")
            chat.chat("你好")
            assert len(chat.history) == 3
            chat.clear_history()
            assert len(chat.history) == 1
            assert isinstance(chat.history[0], SystemMessage)

    def test_switch_model(self, mock_llm):
        new_llm = MagicMock()
        with patch("src.llm.client.create_llm", side_effect=[mock_llm, new_llm]):
            chat = DiagnosticChat("claude")
            chat.switch_model("openai")
            assert chat.provider_name == "openai"
            assert chat.llm == new_llm

    def test_stream_chat(self, mock_llm):
        mock_llm.stream.return_value = [MagicMock(content="你"), MagicMock(content="好")]
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = DiagnosticChat("claude")
            tokens = list(chat.stream_chat("测试"))
            assert tokens == ["你", "好"]
            assert len(chat.history) == 3
