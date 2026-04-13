"""
设备监控 Agent — 持续监控设备状态，检测异常

职责：
- 查询所有设备模块的实时状态
- 读取关键日志，检测异常模式
- 检查固件版本，识别过期组件
- 输出健康状态汇总报告
"""
from langgraph.prebuilt import create_react_agent
from src.llm.client import create_llm
from src.tools.device_status import query_device_status
from src.tools.log_reader import fetch_device_logs
from src.tools.firmware_check import check_firmware_version

MONITOR_SYSTEM_PROMPT = """你是 SMYZE 饮吧设备的监控专家。

你的职责：
1. 全面检查设备各模块的运行状态
2. 读取关键日志，识别异常模式（ERROR、WARN、超时等）
3. 检查软件版本，识别需要更新的组件
4. 输出设备健康状态汇总

你的工具：
- query_device_status: 查询设备模块状态
- fetch_device_logs: 读取设备日志
- check_firmware_version: 检查软件版本

工作流程：
1. 查询所有模块状态（module="all"）
2. 读取中间件日志，过滤 ERROR 关键词
3. 检查所有组件版本
4. 汇总健康状态，标注异常项

输出格式：
- 整体健康评分（正常/警告/异常）
- 各模块状态列表
- 发现的异常和建议
"""

MONITOR_TOOLS = [
    query_device_status,
    fetch_device_logs,
    check_firmware_version,
]


def create_monitor_agent(provider: str = None):
    """创建设备监控 Agent"""
    llm = create_llm(provider)
    return create_react_agent(
        model=llm,
        tools=MONITOR_TOOLS,
        prompt=MONITOR_SYSTEM_PROMPT,
    )
