"""
工具：生成故障诊断报告

学习要点：
1. 结构化输出 —— 工具不只是获取信息，也可以生成格式化的结果
2. 这个工具由 Agent 在收集够信息后主动调用，用于整理诊断结论
"""
from datetime import datetime
from langchain_core.tools import tool


@tool
def generate_diagnosis_report(
    device_id: str,
    fault_description: str,
    root_cause: str,
    severity: str = "中",
    repair_steps: str = "",
    references: str = "",
) -> str:
    """生成结构化的故障诊断报告。在完成故障分析后，使用此工具输出规范化的诊断报告。

    Args:
        device_id: 设备编号，例如 "BAR-001"
        fault_description: 故障现象描述
        root_cause: 故障根因分析
        severity: 严重程度，可选 "高"、"中"、"低"
        repair_steps: 修复步骤建议，多个步骤用换行分隔
        references: 参考文档来源
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""
{'='*50}
📋 设备故障诊断报告
{'='*50}

⏰ 时间: {timestamp}
🏷️ 设备: {device_id}
🔴 严重程度: {severity}

📝 故障现象:
{fault_description}

🔍 根因分析:
{root_cause}

🔧 修复建议:
{repair_steps if repair_steps else "暂无具体修复步骤"}

📄 参考文档:
{references if references else "无"}

{'='*50}
"""
    return report.strip()
