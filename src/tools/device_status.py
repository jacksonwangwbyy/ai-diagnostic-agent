"""
工具：设备状态查询

学习要点：
1. 工具可以调用 HTTP API —— 对接现有业务系统
2. 模拟数据 vs 真实数据 —— 开发阶段先用模拟数据跑通，后续切换到真实接口
"""
import json
from langchain_core.tools import tool


# 模拟数据（开发阶段使用，后续替换为真实 bar-deploy-server API 调用）
MOCK_DEVICES = {
    "BAR-001": {
        "name": "饮吧设备 1号店",
        "status": "online",
        "ip": "192.168.42.1",
        "modules": {
            "coffee_machine": {"status": "normal", "last_heartbeat": "2026-04-09 14:30:00"},
            "ice_machine": {"status": "error", "error_code": "E03", "last_heartbeat": "2026-04-09 14:25:00"},
            "robot_arm": {"status": "normal", "last_heartbeat": "2026-04-09 14:30:00"},
            "display_screen": {"status": "normal", "last_heartbeat": "2026-04-09 14:30:00"},
            "refrigerator": {"status": "warning", "warning": "温度偏高 8°C", "last_heartbeat": "2026-04-09 14:28:00"},
        },
        "software_version": "3.2.1",
        "uptime": "72h",
    },
    "BAR-002": {
        "name": "饮吧设备 2号店",
        "status": "offline",
        "ip": "192.168.42.2",
        "modules": {},
        "software_version": "3.2.0",
        "uptime": "0h",
    },
}


@tool
def query_device_status(device_id: str = "BAR-001") -> str:
    """查询饮吧设备的实时运行状态，包括各模块（咖啡机、制冰机、机械臂、屏幕等）的在线状态、错误信息、心跳时间等。
    当需要了解设备当前运行情况、检查哪些模块有异常时使用此工具。

    Args:
        device_id: 设备编号，例如 "BAR-001"。留空默认查询 BAR-001。
    """
    # TODO: 后续替换为真实 API 调用
    # url = f"{settings.BAR_DEPLOY_SERVER_URL}/api/device/{device_id}/status"
    # response = httpx.get(url)

    device = MOCK_DEVICES.get(device_id)
    if not device:
        available = ", ".join(MOCK_DEVICES.keys())
        return f"未找到设备 {device_id}。可用设备: {available}"

    # 格式化输出
    lines = [
        f"设备: {device['name']} ({device_id})",
        f"状态: {device['status']}",
        f"IP: {device['ip']}",
        f"软件版本: {device['software_version']}",
        f"运行时长: {device['uptime']}",
        "",
        "模块状态:",
    ]

    if not device["modules"]:
        lines.append("  设备离线，无法获取模块状态")
    else:
        for module_name, info in device["modules"].items():
            status = info["status"]
            detail = ""
            if status == "error":
                detail = f" ❌ 错误码: {info.get('error_code', '未知')}"
            elif status == "warning":
                detail = f" ⚠️ {info.get('warning', '')}"
            else:
                detail = " ✅"
            lines.append(f"  {module_name}: {status}{detail}")
            lines.append(f"    最后心跳: {info.get('last_heartbeat', '未知')}")

    return "\n".join(lines)
