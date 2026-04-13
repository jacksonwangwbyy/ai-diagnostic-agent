"""
工具：固件/软件版本检查

查询设备各组件的软件版本，帮助诊断是否因版本过旧导致故障。
"""
import httpx
from langchain_core.tools import tool
from src.config.settings import settings

HTTP_TIMEOUT = 5.0

VERSION_ENDPOINTS = {
    "middleware": "/mid/version",
    "deploy": "/deploy/version",
}


def _fetch_version(path: str) -> dict | None:
    """请求版本信息"""
    url = f"{settings.MIDDLEWARE_BASE_URL}{path}"
    try:
        resp = httpx.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


@tool
def check_firmware_version(component: str = "all") -> str:
    """查询饮吧设备的软件/固件版本信息。
    在排查因版本不兼容或版本过旧导致的故障时使用此工具。

    Args:
        component: 要查询的组件。可选值:
            - "all": 查询所有组件版本（默认）
            - "middleware": 只查询 bar_middleware 版本
            - "deploy": 只查询 bar-deploy-client 版本
    """
    if component != "all" and component not in VERSION_ENDPOINTS:
        available = ", ".join(["all"] + list(VERSION_ENDPOINTS.keys()))
        return f"不支持的组件: {component}。可选: {available}"

    if component != "all":
        path = VERSION_ENDPOINTS[component]
        data = _fetch_version(path)
        if data is None:
            return f"❌ 无法连接到 {component}，服务可能离线。"
        version = data.get("version", "未知")
        return f"📦 {component} 版本: {version}"

    lines = ["=== 设备软件版本信息 ===", ""]
    for name, path in VERSION_ENDPOINTS.items():
        data = _fetch_version(path)
        if data is None:
            lines.append(f"  {name}: ⚠️ 无法获取（服务可能离线）")
        else:
            version = data.get("version", "未知")
            lines.append(f"  {name}: {version}")

    return "\n".join(lines)
