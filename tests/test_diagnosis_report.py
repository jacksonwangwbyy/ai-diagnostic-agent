"""测试：generate_diagnosis_report 工具"""
from datetime import datetime
from src.tools.diagnosis_report import generate_diagnosis_report


class TestGenerateDiagnosisReport:
    """generate_diagnosis_report 是纯函数，无外部依赖"""

    def test_basic_report(self):
        """基本报告生成，包含所有必填字段"""
        result = generate_diagnosis_report.invoke({
            "device_id": "BAR-001",
            "fault_description": "制冰机不出冰",
            "root_cause": "压缩机温度过高，自动保护停机",
        })
        assert "BAR-001" in result
        assert "制冰机不出冰" in result
        assert "压缩机温度过高" in result
        assert "中" in result  # 默认严重程度

    def test_report_with_all_fields(self):
        """完整报告，包含所有可选字段"""
        result = generate_diagnosis_report.invoke({
            "device_id": "BAR-002",
            "fault_description": "咖啡机水温不达标",
            "root_cause": "加热元件老化",
            "severity": "高",
            "repair_steps": "1. 断电\n2. 更换加热元件\n3. 测试水温",
            "references": "咖啡机维修手册 v2.0",
        })
        assert "BAR-002" in result
        assert "高" in result
        assert "加热元件老化" in result
        assert "更换加热元件" in result
        assert "咖啡机维修手册 v2.0" in result

    def test_report_default_severity(self):
        """默认严重程度为"中" """
        result = generate_diagnosis_report.invoke({
            "device_id": "BAR-003",
            "fault_description": "测试",
            "root_cause": "测试原因",
        })
        assert "中" in result

    def test_report_empty_optional_fields(self):
        """可选字段为空时显示默认占位"""
        result = generate_diagnosis_report.invoke({
            "device_id": "BAR-004",
            "fault_description": "故障",
            "root_cause": "原因",
            "repair_steps": "",
            "references": "",
        })
        assert "暂无具体修复步骤" in result

    def test_report_contains_timestamp(self):
        """报告包含时间戳"""
        result = generate_diagnosis_report.invoke({
            "device_id": "BAR-005",
            "fault_description": "测试",
            "root_cause": "测试",
        })
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in result

    def test_report_format_structure(self):
        """报告包含所有结构化部分"""
        result = generate_diagnosis_report.invoke({
            "device_id": "BAR-006",
            "fault_description": "故障描述",
            "root_cause": "原因分析",
        })
        assert "设备故障诊断报告" in result
        assert "故障现象" in result
        assert "根因分析" in result
        assert "修复建议" in result
        assert "参考文档" in result
