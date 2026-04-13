"""
维修建议 Agent — 根据诊断结果生成维修方案

职责：
- 接收故障诊断结论，生成具体维修方案
- 输出：维修步骤、所需备件、预估时间、注意事项
- 工具：知识库搜索（查维修手册）、诊断报告生成
"""
from langgraph.prebuilt import create_react_agent
from src.llm.client import create_llm
from src.tools.knowledge_search import search_knowledge_base
from src.tools.diagnosis_report import generate_diagnosis_report

REPAIR_SYSTEM_PROMPT = """你是 SMYZE 饮吧设备的维修建议专家。

你的职责：
1. 根据故障诊断结论，制定具体的维修方案
2. 列出维修步骤（按顺序，可执行）
3. 列出所需备件和工具
4. 评估维修难度和预估时间
5. 提醒安全注意事项

你的工具：
- search_knowledge_base: 搜索设备维修手册和历史案例
- generate_diagnosis_report: 生成结构化的维修报告

工作流程：
1. 分析收到的故障信息
2. 搜索知识库查找相关维修方案和案例
3. 制定维修步骤
4. 生成结构化报告

注意：
- 维修步骤要具体到操作级别（如"拔掉电源线"而不是"断电"）
- 涉及高压、高温部件时必须提醒安全事项
- 如果故障超出远程维修范围，建议联系现场工程师
"""

REPAIR_TOOLS = [
    search_knowledge_base,
    generate_diagnosis_report,
]


def create_repair_agent(provider: str = None):
    """创建维修建议 Agent"""
    llm = create_llm(provider)
    return create_react_agent(
        model=llm,
        tools=REPAIR_TOOLS,
        prompt=REPAIR_SYSTEM_PROMPT,
    )
