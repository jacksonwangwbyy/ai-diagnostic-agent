"""测试：设备重启工具"""
import subprocess
from unittest.mock import patch, MagicMock
from src.tools.device_restart import restart_device_service


class TestRestartDeviceService:

    def test_restart_middleware(self):
        mock_result = MagicMock(stdout="restarted", stderr="", returncode=0)
        with patch("src.tools.device_restart.subprocess.run", return_value=mock_result):
            result = restart_device_service.invoke({"service": "middleware"})
            assert "成功" in result

    def test_restart_deploy(self):
        mock_result = MagicMock(stdout="restarted", stderr="", returncode=0)
        with patch("src.tools.device_restart.subprocess.run", return_value=mock_result):
            result = restart_device_service.invoke({"service": "deploy"})
            assert "成功" in result

    def test_unsupported_service(self):
        result = restart_device_service.invoke({"service": "rm -rf /"})
        assert "不支持" in result

    def test_ssh_failure(self):
        mock_result = MagicMock(stdout="", stderr="Connection refused", returncode=1)
        with patch("src.tools.device_restart.subprocess.run", return_value=mock_result):
            result = restart_device_service.invoke({"service": "middleware"})
            assert "失败" in result

    def test_ssh_timeout(self):
        with patch("src.tools.device_restart.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=15)):
            result = restart_device_service.invoke({"service": "middleware"})
            assert "超时" in result
