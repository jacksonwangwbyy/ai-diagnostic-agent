"""
工具：设备服务重启

通过 SSH 远程重启指定的设备服务。
安全设计：只允许重启白名单中的服务，不允许执行任意命令。
"""
import subprocess
from langchain_core.tools import tool
from src.config.settings import settings

# 服务重启命令白名单
SERVICE_COMMANDS = {
    "middleware": "systemctl restart bar_middleware",
    "deploy": "systemctl restart bar-deploy-client",
    "docker": "docker restart $(docker ps -q | head -1)",
    "system": "sudo reboot",
}


@tool
def restart_device_service(service: str = "middleware") -> str:
    """重启饮吧设备上的指定服务。
    当故障排查后需要重启服务来恢复设备正常运行时使用此工具。

    Args:
        service: 要重启的服务名。可选值:
            - "middleware": 重启 bar_middleware 中间件服务（默认）
            - "deploy": 重启 bar-deploy-client 部署客户端
            - "docker": 重启 Docker 主容器
            - "system": 整机重启（谨慎使用）
    """
    if service not in SERVICE_COMMANDS:
        available = ", ".join(SERVICE_COMMANDS.keys())
        return f"不支持的服务: {service}。可选: {available}"

    command = SERVICE_COMMANDS[service]

    ssh_cmd = [
        "ssh",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        f"{settings.DEVICE_SSH_USER}@{settings.DEVICE_SSH_HOST}",
        command,
    ]

    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return f"✅ 服务 [{service}] 已重启成功。\n输出: {result.stdout.strip() or '(无输出)'}"
        else:
            error = result.stderr.strip()
            return f"❌ 重启 [{service}] 失败: {error}"

    except subprocess.TimeoutExpired:
        return f"⏰ 重启 [{service}] 超时，设备可能正在重启中，请稍后检查设备状态。"
    except FileNotFoundError:
        return "SSH 客户端未找到，请确认系统已安装 SSH。"
