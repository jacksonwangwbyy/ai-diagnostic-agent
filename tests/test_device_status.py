"""测试：query_device_status 工具"""
from unittest.mock import patch, MagicMock
from src.tools.device_status import (
    _fetch,
    _format_module_status,
    query_device_status,
)


class TestFetch:
    """内部 HTTP 请求函数"""

    def test_fetch_success(self):
        """正常请求返回 JSON"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "data": {}}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.tools.device_status.httpx.get", return_value=mock_resp):
            result = _fetch("/test/path")
            assert result == {"success": True, "data": {}}

    def test_fetch_failure(self):
        """请求失败返回 None"""
        with patch("src.tools.device_status.httpx.get", side_effect=Exception("Connection refused")):
            result = _fetch("/test/path")
            assert result is None


class TestFormatModuleStatus:
    """状态格式化"""

    def test_none_data(self):
        result = _format_module_status("制冰机", None)
        assert "接口无响应" in result

    def test_not_success(self):
        data = {"success": False, "msg": "设备离线"}
        result = _format_module_status("制冰机", data)
        assert "设备离线" in result

    def test_status_list_format(self):
        data = {
            "success": True,
            "data": {
                "status_list": [
                    {"name": "冰块仓", "status": "normal", "error_code": "", "full": True, "inventory": 80},
                ]
            }
        }
        result = _format_module_status("制冰机", data)
        assert "冰块仓" in result
        assert "normal" in result
        assert "满载=是" in result
        assert "库存=80" in result

    def test_status_list_with_error(self):
        data = {
            "success": True,
            "data": {
                "status_list": [
                    {"name": "压缩机", "status": "error", "error_code": "E101"},
                ]
            }
        }
        result = _format_module_status("制冰机", data)
        assert "error" in result
        assert "E101" in result


class TestQueryDeviceStatus:
    """query_device_status 工具"""

    def test_unsupported_module(self):
        result = query_device_status.invoke({"module": "不存在的模块"})
        assert "不支持的模块" in result

    def test_single_module_query(self):
        mock_data = {"success": True, "data": {"status_list": [{"name": "冰块仓", "status": "normal"}]}}
        with patch("src.tools.device_status._fetch", return_value=mock_data):
            result = query_device_status.invoke({"module": "制冰机"})
            assert "制冰机" in result
            assert "normal" in result

    def test_robot_arm_query(self):
        mock_data = {"success": True, "msg": "空闲"}
        with patch("src.tools.device_status._fetch", return_value=mock_data):
            result = query_device_status.invoke({"module": "机械臂"})
            assert "机械臂" in result

    def test_middleware_version_query(self):
        mock_data = {"version": "2.1.0"}
        with patch("src.tools.device_status._fetch", return_value=mock_data):
            result = query_device_status.invoke({"module": "中间件版本"})
            assert "2.1.0" in result

    def test_all_modules_middleware_offline(self):
        with patch("src.tools.device_status._fetch", return_value=None):
            result = query_device_status.invoke({"module": "all"})
            assert "无法连接" in result

    def test_all_modules_success(self):
        version_data = {"version": "2.0.0"}
        module_data = {"success": True, "data": {"status_list": [{"name": "设备", "status": "normal"}]}}
        arm_data = {"success": True, "msg": "空闲"}
        material_data = {"success": True, "data": [{"channel": 1, "currentValue": 100, "source": "A", "category": "水"}]}

        def mock_fetch(path):
            if "version" in path:
                return version_data
            if "RobotArm" in path:
                return arm_data
            if "material" in path:
                return material_data
            return module_data

        with patch("src.tools.device_status._fetch", side_effect=mock_fetch):
            result = query_device_status.invoke({"module": "all"})
            assert "设备状态总览" in result
            assert "2.0.0" in result
