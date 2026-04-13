"""测试：fetch_device_logs 工具及其内部函数"""
from unittest.mock import patch, MagicMock
from src.tools.log_reader import (
    _validate_keyword,
    _read_local,
    _read_ssh,
    fetch_device_logs,
    LOG_PATHS,
)


class TestValidateKeyword:
    """keyword 白名单校验"""

    def test_valid_keywords(self):
        assert _validate_keyword("") is None
        assert _validate_keyword("error") is None
        assert _validate_keyword("ERROR") is None
        assert _validate_keyword("timeout-error") is None
        assert _validate_keyword("app.log") is None
        assert _validate_keyword("error code 500") is None
        assert _validate_keyword("test_123") is None

    def test_invalid_keywords(self):
        assert _validate_keyword("$(rm -rf /)") is not None
        assert _validate_keyword("'; DROP TABLE") is not None
        assert _validate_keyword("keyword|pipe") is not None


class TestReadLocal:
    """本地日志读取"""

    def test_read_file_log(self, tmp_log_file):
        """读取本地日志文件"""
        with patch.dict(LOG_PATHS, {"syslog": str(tmp_log_file)}):
            result = _read_local("syslog", 3, "")
            assert "设备日志 - syslog" in result
            assert "最近 3 行" in result

    def test_read_with_keyword_filter(self, tmp_log_file):
        """关键词过滤"""
        with patch.dict(LOG_PATHS, {"syslog": str(tmp_log_file)}):
            result = _read_local("syslog", 50, "ERROR")
            assert "ERROR" in result
            assert "过滤: 'ERROR'" in result
            assert "系统启动" not in result

    def test_file_not_exists(self):
        """日志文件不存在"""
        with patch.dict(LOG_PATHS, {"syslog": "/nonexistent/path/log.txt"}):
            result = _read_local("syslog", 50, "")
            assert "日志文件不存在" in result

    def test_docker_no_container(self):
        """Docker 模式但无运行容器"""
        mock_result = MagicMock(stdout="", returncode=0)
        with patch("src.tools.log_reader.subprocess.run", return_value=mock_result):
            result = _read_local("docker", 50, "")
            assert "没有运行中的 Docker 容器" in result

    def test_docker_with_container(self):
        """Docker 模式正常读取"""
        ps_result = MagicMock(stdout="abc123\n", returncode=0)
        log_result = MagicMock(stdout="log line 1\nlog line 2", stderr="", returncode=0)
        with patch("src.tools.log_reader.subprocess.run", side_effect=[ps_result, log_result]):
            result = _read_local("docker", 50, "")
            assert "Docker 日志" in result
            assert "log line 1" in result

    def test_empty_log_with_keyword(self, tmp_log_file):
        """关键词过滤后结果为空"""
        with patch.dict(LOG_PATHS, {"syslog": str(tmp_log_file)}):
            result = _read_local("syslog", 50, "NONEXISTENT_KEYWORD")
            assert "日志为空" in result


class TestReadSSH:
    """SSH 远程日志读取"""

    def test_ssh_success(self):
        """SSH 正常读取"""
        mock_result = MagicMock(stdout="log line 1\nlog line 2", stderr="", returncode=0)
        with patch("src.tools.log_reader.subprocess.run", return_value=mock_result):
            result = _read_ssh("syslog", 50, "")
            assert "设备日志 - syslog" in result
            assert "log line 1" in result

    def test_ssh_connection_refused(self):
        """SSH 连接被拒绝"""
        mock_result = MagicMock(stdout="", stderr="Connection refused", returncode=1)
        with patch("src.tools.log_reader.subprocess.run", return_value=mock_result):
            result = _read_ssh("syslog", 50, "")
            assert "无法连接到设备" in result

    def test_ssh_timeout(self):
        """SSH 连接超时"""
        import subprocess
        with patch(
            "src.tools.log_reader.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=15),
        ):
            result = _read_ssh("syslog", 50, "")
            assert "SSH 连接超时" in result

    def test_ssh_not_found(self):
        """SSH 客户端未安装"""
        with patch("src.tools.log_reader.subprocess.run", side_effect=FileNotFoundError()):
            result = _read_ssh("syslog", 50, "")
            assert "SSH 客户端未找到" in result

    def test_ssh_with_keyword(self):
        """SSH 模式带关键词"""
        mock_result = MagicMock(stdout="error line", stderr="", returncode=0)
        with patch("src.tools.log_reader.subprocess.run", return_value=mock_result) as mock_run:
            result = _read_ssh("syslog", 50, "error")
            assert "过滤: 'error'" in result
            call_args = mock_run.call_args[0][0]
            ssh_command = call_args[-1]
            assert "grep" in ssh_command


class TestFetchDeviceLogs:
    """fetch_device_logs 工具入口"""

    def test_invalid_log_type(self):
        result = fetch_device_logs.invoke({"log_type": "invalid", "lines": 50, "keyword": ""})
        assert "不支持的日志类型" in result

    def test_lines_out_of_range_zero(self):
        result = fetch_device_logs.invoke({"log_type": "syslog", "lines": 0, "keyword": ""})
        assert "1-1000" in result

    def test_lines_out_of_range_over(self):
        result = fetch_device_logs.invoke({"log_type": "syslog", "lines": 1001, "keyword": ""})
        assert "1-1000" in result

    def test_invalid_keyword(self):
        result = fetch_device_logs.invoke({"log_type": "syslog", "lines": 50, "keyword": "$(rm -rf /)"})
        assert "非法字符" in result

    def test_dispatch_to_local(self, tmp_log_file):
        """local 模式分发到 _read_local"""
        with patch.dict(LOG_PATHS, {"syslog": str(tmp_log_file)}):
            with patch("src.tools.log_reader.settings") as mock_settings:
                mock_settings.LOG_READ_MODE = "local"
                result = fetch_device_logs.invoke({"log_type": "syslog", "lines": 50, "keyword": ""})
                assert "设备日志" in result
