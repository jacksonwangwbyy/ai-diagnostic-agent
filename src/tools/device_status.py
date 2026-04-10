"""
工具：设备状态查询（真实 API 版）

对接 bar_middleware 的 /machine/status 接口，获取各硬件模块的真实运行状态。
bar_middleware 运行在同一台主机上，默认 http://localhost:8003。
"""
import httpx
from langchain_core.tools import tool
from src.config.settings import settings

# 各硬件模块的状态接口映射
# key: 模块名（给 Agent 看的）, value: API 路径
MODULE_STATUS_ENDPOINTS = {
    "制冰机": "/ice/machine/status",
    "咖啡机": "/coffee/machine/status",
    "杯子机": "/cup/machine/status",
    "扣盖机": "/lid/machine/status",
    "电源": "/power/machine/status",
    "饮料机": "/beverage/machine/status",
    "冰淇淋机": "/icecream/machine/status",
    "糖浆机": "/syrup/machine/status",
    "粉料机": "/powder/machine/status",
    "打印机": "/printer/machine/status",
    "冷凝器": "/cc/machine/status",
}

# 需要单独处理的接口
SPECIAL_ENDPOINTS = {
    "机械臂": "/RobotArm/Dev/status",
    "物料": "/agent/material/all",
    "监控设备": "/agent/monitor/status",
    "电子锁": "/elock/status",
    "中间件版本": "/mid/version",
}

HTTP_TIMEOUT = 5.0  # 秒


def _fetch(path: str) -> dict | None:
    """请求 bar_middleware 接口，返回 JSON 或 None"""
    url = f"{settings.MIDDLEWARE_BASE_URL}{path}"
    try:
        resp = httpx.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _format_module_status(name: str, data: dict | None) -> str:
    """格式化单个模块的状态输出"""
    if data is None:
        return f"  {name}: ⚠️ 接口无响应（模块可能未启用或离线）"

    success = data.get("success", False)
    if not success:
        msg = data.get("msg", "未知错误")
        return f"  {name}: ❌ {msg}"

    # 标准 machine/status 返回格式: data.status_list[{code, name, status, ...}]
    inner = data.get("data", {})

    # 处理 status_list 格式
    if isinstance(inner, dict) and "status_list" in inner:
        lines = []
        for item in inner["status_list"]:
            item_name = item.get("name", name)
            status = item.get("status", "unknown")
            error_code = item.get("error_code", "")
            full = item.get("full")
            inventory = item.get("inventory")

            detail_parts = [f"状态={status}"]
            if error_code:
                detail_parts.append(f"错误码={error_code}")
            if full is not None:
                detail_parts.append(f"满载={'是' if full else '否'}")
            if inventory is not None:
                detail_parts.append(f"库存={inventory}")

            lines.append(f"  {item_name}: {', '.join(detail_parts)}")
        return "\n".join(lines) if lines else f"  {name}: ✅ 正常"

    # 其他格式，直接输出
    return f"  {name}: {inner}"


@tool
def query_device_status(module: str = "all") -> str:
    """查询饮吧设备各硬件模块的实时运行状态。
    可查询制冰机、咖啡机、机械臂、杯子机、扣盖机、电源、饮料机、冰淇淋机、糖浆机、粉料机等模块。

    Args:
        module: 要查询的模块名。可选值:
            - "all": 查询所有模块（默认）
            - "制冰机" / "咖啡机" / "机械臂" / "杯子机" / "扣盖机"
            - "电源" / "饮料机" / "冰淇淋机" / "糖浆机" / "粉料机"
            - "物料" / "监控设备" / "电子锁" / "打印机" / "冷凝器"
            - "中间件版本"
    """
    all_endpoints = {**MODULE_STATUS_ENDPOINTS, **SPECIAL_ENDPOINTS}

    if module != "all":
        # 查询单个模块
        path = all_endpoints.get(module)
        if not path:
            available = ", ".join(all_endpoints.keys())
            return f"不支持的模块: {module}。可选: {available}"

        data = _fetch(path)

        # 机械臂和物料的返回格式不同，特殊处理
        if module == "机械臂":
            if data and data.get("success"):
                return f"机械臂状态:\n  {data.get('msg', {})}"
            return "机械臂: ⚠️ 无法获取状态"

        if module == "中间件版本":
            if data:
                return f"中间件版本: {data.get('version', '未知')}"
            return "中间件: ⚠️ 无法连接"

        return f"[{module}] 状态:\n{_format_module_status(module, data)}"

    # 查询所有模块
    lines = ["=== 饮吧设备状态总览 ===", ""]

    # 先检查中间件是否在线
    version_data = _fetch("/mid/version")
    if version_data is None:
        return "❌ 无法连接到 bar_middleware，中间件可能未启动。"
    lines.append(f"中间件版本: {version_data.get('version', '未知')}")
    lines.append("")

    # 查询所有标准模块
    lines.append("--- 硬件模块状态 ---")
    for name, path in MODULE_STATUS_ENDPOINTS.items():
        data = _fetch(path)
        lines.append(_format_module_status(name, data))

    # 机械臂
    arm_data = _fetch(SPECIAL_ENDPOINTS["机械臂"])
    if arm_data and arm_data.get("success"):
        lines.append(f"  机械臂: {arm_data.get('msg', {})}")
    else:
        lines.append("  机械臂: ⚠️ 无法获取状态")

    # 物料
    lines.append("")
    lines.append("--- 物料状态 ---")
    material_data = _fetch(SPECIAL_ENDPOINTS["物料"])
    if material_data and material_data.get("success"):
        materials = material_data.get("data", [])
        if materials:
            for m in materials[:10]:  # 最多显示 10 条
                channel = m.get("channel", "?")
                value = m.get("currentValue", "?")
                source = m.get("source", "")
                category = m.get("category", "")
                lines.append(f"  通道 {channel} ({source}/{category}): {value}")
            if len(materials) > 10:
                lines.append(f"  ... 共 {len(materials)} 条物料数据")
        else:
            lines.append("  暂无物料数据")
    else:
        lines.append("  物料: ⚠️ 无法获取")

    return "\n".join(lines)
