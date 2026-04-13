"""测试：维修建议 Agent"""
from unittest.mock import patch, MagicMock
from src.agent.repair_agent import create_repair_agent, REPAIR_TOOLS, REPAIR_SYSTEM_PROMPT


class TestRepairAgent:

    def test_create_repair_agent(self):
        """能正常创建维修 Agent"""
        mock_llm = MagicMock()
        with patch("src.agent.repair_agent.create_llm", return_value=mock_llm):
            with patch("src.agent.repair_agent.create_react_agent") as mock_create:
                mock_create.return_value = MagicMock()
                agent = create_repair_agent("claude")
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["model"] == mock_llm
                assert call_kwargs["prompt"] == REPAIR_SYSTEM_PROMPT

    def test_repair_tools_count(self):
        """维修 Agent 有 2 个工具"""
        assert len(REPAIR_TOOLS) == 2

    def test_repair_tools_names(self):
        """维修 Agent 工具名称正确"""
        tool_names = {t.name for t in REPAIR_TOOLS}
        assert "search_knowledge_base" in tool_names
        assert "generate_diagnosis_report" in tool_names

    def test_system_prompt_content(self):
        """系统提示词包含关键指导"""
        assert "维修" in REPAIR_SYSTEM_PROMPT
        assert "备件" in REPAIR_SYSTEM_PROMPT
        assert "安全" in REPAIR_SYSTEM_PROMPT
