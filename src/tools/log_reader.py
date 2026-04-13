"""
工具：设备日志读取

学习要点：
1. 支持两种模式：本地文件读取（同机部署）和 SSH 远程读取
2. 通过 LOG_READ_MODE 配置项切换，代码逻辑完全隔离
3. 错误处理 - 工具调用失败时要返回可理解的错误信息，而不是抛异常
"""
import re
import shlex
import subprocess
from pathlib import Path
from langchain_core.tools import tool
from src.config.settings import settings

# 日志路径映射
LOG_PATHS = {
    "syslog": "/var/log/syslog",
    "middleware": "/home/smyze/bar_middleware/logs/app.log",
    "deploy": "/home/smyze/bar-deploy-client/logs/app.log",
    "docker": None,  # 特殊处理
}

# keyword 白名单：只允许字母、数字、空格、连字符、点、下划线
_KEYWORD_RE = re.compile(r'^[\w\s\-\.]*$')


def _validate_keyword(keyword: str) -> str | None:
    """校验 keyword，返回错误信息或 None（合法）"""
    if keyword and not _KEYWORD_RE.match(keyword):
        return "keyword 包含非法字符，只允许字母、数字、空格、连字符、点、下划线"
    return None


def _read_local(log_type: str, lines: int, keyword: str) -> str:
    """本地模式：直接读取文件"""
    if log_type == "docker":
        try:
            ps_result = subprocess.run(
                ["docker", "ps", "-q", "--no-trunc"],
                capture_output=True, text=True, timeout=5,
            )
            container_id = ps_result.stdout.strip().split("\n")[0] if ps_result.stdout.strip() else ""
            if not container_id:
                return "没有运行中的 Docker 容器"

            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container_id],
                capture_output=True, text=True, timeout=15,
            )
            output = result.stdout.strip() or result.stderr.strip()
            return f"[Docker 日志] 最近 {lines} 行:\n\n{output}" if output else "Docker 日志为空"
        except Exception as e:
            return f"读取 Docker 日志失败: {e}"

    raw_path = LOG_PATHS.get(log_type)
    if raw_path is None:
        return f"日志类型 {log_type} 无本地路径配置"
    log_path = Path(raw_path)
    if not log_path.exists():
        return f"日志文件不存在: {log_path}"

    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()

        if keyword:
            all_lines = [l for l in all_lines if keyword.lower() in l.lower()]

        recent = all_lines[-lines:]
        if not recent:
            return f"日志为空（类型: {log_type}，关键词: '{keyword}'）"

        header = f"[设备日志 - {log_type}] 最近 {lines} 行"
        if keyword:
            header += f" (过滤: '{keyword}')"
        return f"{header}:\n\n{''.join(recent)}"

    except Exception as e:
        return f"读取日志文件失败: {e}"


def _read_ssh(log_type: str, lines: int, keyword: str) -> str:
    """SSH 模式：远程读取（使用参数列表避免命令注入）"""
    if log_type == "docker":
        # docker 命令不含用户输入，字符串拼接安全
        remote_cmd = f"docker logs --tail {lines} $(docker ps -q | head -1) 2>&1"
        ssh_args = [remote_cmd]
    else:
        log_path = LOG_PATHS[log_type]
        if keyword:
            # 通过 SSH 传递参数列表：grep -i -e KEYWORD FILE
            remote_cmd = f"grep -i -e {shlex.quote(keyword)} {log_path} | tail -n {lines}"
        else:
            remote_cmd = f"tail -n {lines} {log_path}"
        ssh_args = [remote_cmd]

    ssh_cmd = [
        "ssh",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        f"{settings.DEVICE_SSH_USER}@{settings.DEVICE_SSH_HOST}",
        *ssh_args,
    ]

    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)

        if result.returncode != 0:
            error = result.stderr.strip()
            if "Connection refused" in error or "Connection timed out" in error:
                return f"无法连接到设备 {settings.DEVICE_SSH_HOST}，设备可能离线。"
            return f"读取日志失败: {error}"

        output = result.stdout.strip()
        if not output:
            return f"日志为空（类型: {log_type}，关键词: '{keyword}'）"

        header = f"[设备日志 - {log_type}] 最近 {lines} 行"
        if keyword:
            header += f" (过滤: '{keyword}')"
        return f"{header}:\n\n{output}"

    except subprocess.TimeoutExpired:
        return f"SSH 连接超时，设备 {settings.DEVICE_SSH_HOST} 可能无法访问。"
    except FileNotFoundError:
        return "SSH 客户端未找到，请确认系统已安装 SSH。"


@tool
def fetch_device_logs(
    log_type: str = "syslog",
    lines: int = 50,
    keyword: str = "",
) -> str:
    """读取饮吧设备的运行日志。
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
    if log_type not in LOG_PATHS:
        return f"不支持的日志类型: {log_type}。支持: {', '.join(LOG_PATHS.keys())}"

    if not isinstance(lines, int) or lines <= 0 or lines > 1000:
        return "lines 参数必须为 1-1000 之间的整数"

    err = _validate_keyword(keyword)
    if err:
        return err

    if settings.LOG_READ_MODE == "local":
        return _read_local(log_type, lines, keyword)
    else:
        return _read_ssh(log_type, lines, keyword)
