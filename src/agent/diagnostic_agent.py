"""
诊断 Agent - 核心编排模块

学习要点：
1. ReAct 模式 - Reasoning + Acting 的循环
   Agent 的工作流程：
   Thought（思考）→ Action（调用工具）→ Observation（观察结果）→ 重复...→ Final Answer

2. create_react_agent - LangChain 创建 ReAct Agent 的标准方式
   它会自动处理：工具选择、参数填充、结果解析、循环控制

3. Agent 和 Chain 的区别：
   - Chain：固定流程，A → B → C
   - Agent：动态决策，根据上下文自主决定下一步做什么

4. 工具注册：Agent 通过工具的 name 和 description 来决定何时调用哪个工具
   所以工具的 description 写得好不好，直接影响 Agent 的智能程度
"""
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from src.llm.client import create_llm
from src.tools.knowledge_search import search_knowledge_base
from src.tools.log_reader import fetch_device_logs
from src.tools.device_status import query_device_status
from src.tools.diagnosis_report import generate_diagnosis_report


# Agent 系统提示词
AGENT_SYSTEM_PROMPT = """你是 SMYZE 饮吧设备的智能故障诊断 Agent。

你的能力：
1. 查询设备实时状态（query_device_status）
2. 读取设备运行日志（fetch_device_logs）
3. 检索设备知识库（search_knowledge_base）
4. 生成故障诊断报告（generate_diagnosis_report）

你的工作流程：
1. 接收用户描述的故障现象
2. 先查询设备状态，了解当前各模块的运行情况
3. 根据故障现象读取相关日志，寻找错误信息
4. 搜索知识库，查找类似故障案例和技术文档
5. 综合分析后，生成结构化的诊断报告

注意事项：
- 每次诊断至少使用 2-3 个工具来收集信息
- 不要猜测，要基于实际数据进行分析
- 如果信息不足，主动使用工具获取更多信息
- 最终要给出具体可执行的修复建议
"""

# 注册所有工具
TOOLS = [
    search_knowledge_base,
    fetch_device_logs,
    query_device_status,
    generate_diagnosis_report,
]


def create_diagnostic_agent(provider: str = None):
    """
    创建诊断 Agent

    Args:
        provider: LLM provider（claude/openai）

    Returns:
        可调用的 Agent（LangGraph 编译后的图）
    """
    llm = create_llm(provider)

    agent = create_react_agent(
        model=llm,
        tools=TOOLS,
        prompt=AGENT_SYSTEM_PROMPT,
    )

    return agent


def run_diagnosis(question: str, provider: str = None, verbose: bool = True) -> str:
    """
    执行一次故障诊断

    Args:
        question: 用户描述的故障问题
        provider: LLM provider
        verbose: 是否打印中间推理过程

    Returns:
        最终诊断结果
    """
    agent = create_diagnostic_agent(provider)

    if verbose:
        print(f"\n{'='*50}")
        print(f"🔧 开始诊断: {question}")
        print(f"{'='*50}\n")

    # 执行 Agent
    result = agent.invoke({
        "messages": [HumanMessage(content=question)],
    })

    # 提取最终回复
    messages = result["messages"]

    if verbose:
        # 打印推理过程
        for msg in messages:
            msg_type = type(msg).__name__
            if msg_type == "HumanMessage":
                print(f"🧑 用户: {msg.content[:100]}")
            elif msg_type == "AIMessage":
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"🤖 调用工具: {tc['name']}({tc['args']})")
                elif msg.content:
                    content = msg.content
                    if isinstance(content, list):
                        content = "".join(
                            block["text"] for block in content
                            if isinstance(block, dict) and block.get("type") == "text"
                        )
                    print(f"🤖 回复: {content[:200]}...")
            elif msg_type == "ToolMessage":
                print(f"🔧 工具结果: [{msg.name}] {msg.content[:150]}...")
            print()

    # 返回最后一条 AI 消息
    final_msg = messages[-1]
    content = final_msg.content
    if isinstance(content, list):
        content = "".join(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return content
