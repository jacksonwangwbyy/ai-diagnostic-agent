"""测试：Supervisor 编排引擎"""
from unittest.mock import patch, MagicMock
from src.agent.supervisor import _route_by_keywords, _extract_final_answer, run_multi_agent
from langchain_core.messages import AIMessage


class TestRouteByKeywords:

    def test_diagnose_default(self):
        assert _route_by_keywords("制冰机不工作了") == "diagnose"

    def test_repair_route(self):
        assert _route_by_keywords("怎么维修制冰机") == "repair"

    def test_monitor_route(self):
        assert _route_by_keywords("检查所有设备状态") == "monitor"

    def test_diagnose_plus_repair(self):
        assert _route_by_keywords("制冰机故障了，怎么修") == "diagnose+repair"

    def test_unknown_defaults_to_diagnose(self):
        assert _route_by_keywords("你好") == "diagnose"


class TestExtractFinalAnswer:

    def test_extracts_last_ai_message(self):
        msg = AIMessage(content="最终回答")
        result = _extract_final_answer({"messages": [msg]})
        assert result == "最终回答"

    def test_empty_messages(self):
        result = _extract_final_answer({"messages": []})
        assert "未能" in result


class TestRunMultiAgent:

    def _make_agent_result(self, content: str) -> dict:
        return {"messages": [AIMessage(content=content)]}

    def test_diagnose_route(self):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = self._make_agent_result("诊断结论")

        with patch("src.agent.supervisor.create_diagnostic_agent", return_value=mock_agent):
            with patch("src.agent.supervisor.create_llm", return_value=MagicMock()):
                result = run_multi_agent("制冰机报错了")
                assert result["route"] == "diagnose"
                assert "diagnostic" in result["agents_used"]
                assert result["result"] == "诊断结论"

    def test_repair_route(self):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = self._make_agent_result("维修方案")

        with patch("src.agent.supervisor.create_repair_agent", return_value=mock_agent):
            with patch("src.agent.supervisor.create_llm", return_value=MagicMock()):
                result = run_multi_agent("怎么维修制冰机")
                assert result["route"] == "repair"
                assert "repair" in result["agents_used"]

    def test_monitor_route(self):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = self._make_agent_result("设备状态正常")

        with patch("src.agent.supervisor.create_monitor_agent", return_value=mock_agent):
            with patch("src.agent.supervisor.create_llm", return_value=MagicMock()):
                result = run_multi_agent("检查所有设备状态")
                assert result["route"] == "monitor"
                assert "monitor" in result["agents_used"]

    def test_diagnose_plus_repair_chain(self):
        diag_agent = MagicMock()
        diag_agent.invoke.return_value = self._make_agent_result("诊断：压缩机过热")
        repair_agent = MagicMock()
        repair_agent.invoke.return_value = self._make_agent_result("维修：更换压缩机")

        with patch("src.agent.supervisor.create_diagnostic_agent", return_value=diag_agent):
            with patch("src.agent.supervisor.create_repair_agent", return_value=repair_agent):
                with patch("src.agent.supervisor.create_llm", return_value=MagicMock()):
                    result = run_multi_agent("制冰机故障了，怎么修")
                    assert result["route"] == "diagnose+repair"
                    assert "diagnostic" in result["agents_used"]
                    assert "repair" in result["agents_used"]
                    assert "诊断" in result["result"]
                    assert "维修" in result["result"]
