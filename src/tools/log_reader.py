"""
工具：设备日志读取

学习要点：
1. 工具可以调用外部系统（SSH）—— 这是 Agent 的核心能力
2. 参数校验 - 通过 docstring 定义参数类型和说明
3. 错误处理 - 工具调用失败时要返回可理解的错误信息，而不是抛异常
"""
import subprocess
from langchain_core.tools import tool
from src.config.settings import settings


@tool
def fetch_device_logs(
    log_type: str = "syslog",
    lines: int = 50,
    keyword: str = "",
) -> str:
    """通过 SSH 读取饮吧设备的运行日志。
    当需要查看设备的实时日志、错误日志、历史运行记录来排查故障时使用此工具。

    Args:
        log_type: 日志类型。可选值:
            - "syslog": 系统日志（默认）
            - "middleware": 中间件日志（bar_middleware）
            - "deploy": 部署客户端日志（bar-deploy-client）
            - "docker": Docker 容器日志
        lines: 读取的日志行数，默认 50
        keyword: 过滤关键词，只返回包含该关键词的日志行，留空表示不过滤
    """
    # 构造远程命令
    log_paths = {
        "syslog": "/var/log/syslog",
        "middleware": "/home/smyze/bar_middleware/logs/app.log",
        "deploy": "/home/smyze/bar-deploy-client/logs/app.log",
        "docker": None,  # 特殊处理
    }

    if log_type not in log_paths:
        return f"不支持的日志类型: {log_type}。支持: {', '.join(log_paths.keys())}"

    if log_type == "docker":
        remote_cmd = f"docker logs --tail {lines} $(docker ps -q | head -1) 2>&1"
    else:
        log_path = log_paths[log_type]
        if keyword:
            remote_cmd = f"grep -i '{keyword}' {log_path} | tail -n {lines}"
        else:
            remote_cmd = f"tail -n {lines} {log_path}"

    # 通过 SSH 执行
    ssh_cmd = [
        "ssh",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        f"{settings.DEVICE_SSH_USER}@{settings.DEVICE_SSH_HOST}",
        remote_cmd,
    ]

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            error = result.stderr.strip()
            if "Connection refused" in error or "Connection timed out" in error:
                return f"无法连接到设备 {settings.DEVICE_SSH_HOST}，设备可能离线。"
            return f"读取日志失败: {error}"

        output = result.stdout.strip()
        if not output:
            return f"日志为空（类型: {log_type}，关键词: '{keyword}'）"

        return f"[设备日志 - {log_type}] 最近 {lines} 行" + (
            f" (过滤: '{keyword}')" if keyword else ""
        ) + f":\n\n{output}"

    except subprocess.TimeoutExpired:
        return f"SSH 连接超时，设备 {settings.DEVICE_SSH_HOST} 可能无法访问。"
    except FileNotFoundError:
        return "SSH 客户端未找到，请确认系统已安装 SSH。"
