"""
Supervisor Agent — 多 Agent 编排引擎

职责：
1. 接收用户请求，识别意图
2. 路由到对应专业 Agent（诊断/维修/监控）
3. 汇总结果返回

路由策略：
- 故障/报错/不工作 → 诊断 Agent
- 维修/怎么修/备件 → 维修 Agent
- 状态/健康/检查 → 监控 Agent
- 复杂故障 → 诊断 Agent → 维修 Agent（链式）
"""
import logging
from langchain_core.messages import HumanMessage, AIMessage
from src.llm.client import create_llm, extract_text
from src.agent.diagnostic_agent import create_diagnostic_agent
from src.agent.repair_agent import create_repair_agent
from src.agent.monitor_agent import create_monitor_agent

logger = logging.getLogger(__name__)

# 路由意图关键词
_REPAIR_KEYWORDS = {"维修", "怎么修", "修复", "备件", "更换", "拆卸", "安装", "维护"}
_MONITOR_KEYWORDS = {"状态", "健康", "检查", "监控", "巡检", "所有模块", "整体", "概况"}
_DIAGNOSE_KEYWORDS = {"故障", "报错", "不工作", "异常", "失败", "错误", "问题", "坏了"}

ROUTE_PROMPT = """你是一个请求路由器。根据用户请求，判断应该由哪个 Agent 处理。

可选 Agent：
- "diagnose": 故障诊断（设备报错、不工作、异常）
- "repair": 维修建议（如何修复、备件清单、操作步骤）
- "monitor": 设备监控（整体状态检查、健康巡检）
- "diagnose+repair": 先诊断再给维修方案（复杂故障）

只输出 Agent 名称，不要解释。

用户请求：{question}
路由到："""


def _route_by_keywords(question: str) -> str:
    """基于关键词的快速路由（不需要 LLM）"""
    q = question.lower()
    has_repair = any(kw in q for kw in _REPAIR_KEYWORDS)
    has_monitor = any(kw in q for kw in _MONITOR_KEYWORDS)
    has_diagnose = any(kw in q for kw in _DIAGNOSE_KEYWORDS)

    if has_repair and not has_diagnose:
        return "repair"
    if has_monitor and not has_diagnose:
        return "monitor"
    if has_repair and has_diagnose:
        return "diagnose+repair"
    if has_monitor and has_diagnose:
        return "diagnose"  # 监控+诊断意图，优先诊断
    return "diagnose"  # 默认


def _route_by_llm(question: str, llm) -> str:
    """使用 LLM 进行精确路由"""
    try:
        response = llm.invoke([
            HumanMessage(content=ROUTE_PROMPT.format(question=question))
        ])
        route = extract_text(response.content).strip().lower()
        valid = {"diagnose", "repair", "monitor", "diagnose+repair"}
        return route if route in valid else "diagnose"
    except Exception as e:
        logger.warning(f"LLM 路由失败，使用关键词路由: {e}")
        return _route_by_keywords(question)


def _extract_final_answer(result: dict) -> str:
    """从 Agent 结果中提取最终回答"""
    messages = result.get("messages", [])
    ai_messages = [m for m in messages if isinstance(m, AIMessage) and m.content]
    if ai_messages:
        return extract_text(ai_messages[-1].content)
    return "Agent 未能生成回答"


def run_multi_agent(
    question: str,
    provider: str = None,
    use_llm_routing: bool = False,
) -> dict:
    """
    多 Agent 协作入口

    Args:
        question: 用户请求
        provider: LLM provider
        use_llm_routing: 是否使用 LLM 路由（默认关键词路由）

    Returns:
        {
            "result": 最终回答,
            "route": 路由路径,
            "agents_used": 使用的 Agent 列表,
        }
    """
    llm = create_llm(provider)

    # 路由决策
    if use_llm_routing:
        route = _route_by_llm(question, llm)
    else:
        route = _route_by_keywords(question)

    logger.info(f"路由决策: '{question[:50]}' → {route}")

    agents_used = []
    final_result = ""

    if route == "diagnose":
        agent = create_diagnostic_agent(provider)
        result = agent.invoke({"messages": [HumanMessage(content=question)]})
        final_result = _extract_final_answer(result)
        agents_used = ["diagnostic"]

    elif route == "repair":
        agent = create_repair_agent(provider)
        result = agent.invoke({"messages": [HumanMessage(content=question)]})
        final_result = _extract_final_answer(result)
        agents_used = ["repair"]

    elif route == "monitor":
        agent = create_monitor_agent(provider)
        result = agent.invoke({"messages": [HumanMessage(content=question)]})
        final_result = _extract_final_answer(result)
        agents_used = ["monitor"]

    elif route == "diagnose+repair":
        # 链式：先诊断，再基于诊断结果给维修方案
        diag_agent = create_diagnostic_agent(provider)
        diag_result = diag_agent.invoke({"messages": [HumanMessage(content=question)]})
        diagnosis = _extract_final_answer(diag_result)
        agents_used.append("diagnostic")

        repair_question = f"设备故障描述：{question}\n\n诊断结论：\n{diagnosis}\n\n请给出具体维修方案。"
        repair_agent = create_repair_agent(provider)
        repair_result = repair_agent.invoke({"messages": [HumanMessage(content=repair_question)]})
        repair_plan = _extract_final_answer(repair_result)
        agents_used.append("repair")

        final_result = f"## 故障诊断\n\n{diagnosis}\n\n## 维修方案\n\n{repair_plan}"

    return {
        "result": final_result,
        "route": route,
        "agents_used": agents_used,
    }
