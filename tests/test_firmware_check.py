"""测试：固件版本检查工具"""
from unittest.mock import patch, MagicMock
from src.tools.firmware_check import check_firmware_version


class TestCheckFirmwareVersion:

    def test_version_check_all(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"version": "2.1.0"}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.tools.firmware_check.httpx.get", return_value=mock_resp):
            result = check_firmware_version.invoke({})
            assert "2.1.0" in result
            assert "设备软件版本信息" in result

    def test_check_specific_component(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"version": "1.5.3"}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.tools.firmware_check.httpx.get", return_value=mock_resp):
            result = check_firmware_version.invoke({"component": "middleware"})
            assert "1.5.3" in result

    def test_middleware_offline(self):
        with patch("src.tools.firmware_check.httpx.get", side_effect=Exception("Connection refused")):
            result = check_firmware_version.invoke({"component": "middleware"})
            assert "无法连接" in result

    def test_unsupported_component(self):
        result = check_firmware_version.invoke({"component": "invalid"})
        assert "不支持" in result
