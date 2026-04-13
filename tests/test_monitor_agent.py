"""测试：设备监控 Agent"""
from unittest.mock import patch, MagicMock
from src.agent.monitor_agent import create_monitor_agent, MONITOR_TOOLS, MONITOR_SYSTEM_PROMPT


class TestMonitorAgent:

    def test_create_monitor_agent(self):
        mock_llm = MagicMock()
        with patch("src.agent.monitor_agent.create_llm", return_value=mock_llm):
            with patch("src.agent.monitor_agent.create_react_agent") as mock_create:
                mock_create.return_value = MagicMock()
                create_monitor_agent("claude")
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["model"] == mock_llm
                assert call_kwargs["prompt"] == MONITOR_SYSTEM_PROMPT

    def test_monitor_tools_count(self):
        assert len(MONITOR_TOOLS) == 3

    def test_monitor_tools_names(self):
        tool_names = {t.name for t in MONITOR_TOOLS}
        assert "query_device_status" in tool_names
        assert "fetch_device_logs" in tool_names
        assert "check_firmware_version" in tool_names

    def test_system_prompt_content(self):
        assert "监控" in MONITOR_SYSTEM_PROMPT
        assert "异常" in MONITOR_SYSTEM_PROMPT
        assert "版本" in MONITOR_SYSTEM_PROMPT
