# 迭代 1：基础质量保障 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理重复代码、填充故障案例知识库、构建完整测试套件，确保项目代码质量和数据完整性。

**Architecture:** 三个独立任务依次执行：(1) 清理 log_reader.py 中的重复函数定义 (2) 生成 20+ 模拟故障案例填充到 knowledge-base/fault-cases/ (3) 使用 pytest + pytest-asyncio 构建覆盖所有模块的测试套件。

**Tech Stack:** Python 3.11, pytest, pytest-asyncio, unittest.mock, FastAPI TestClient (httpx.AsyncClient)

---

## 文件结构

### 修改文件
- `src/tools/log_reader.py` — 删除重复的函数定义（行 164-277）

### 新建文件
- `knowledge-base/fault-cases/middleware-faults.md` — 中间件相关故障案例
- `knowledge-base/fault-cases/robot-arm-faults.md` — 机械臂相关故障案例
- `knowledge-base/fault-cases/material-monitor-faults.md` — 物料监控相关故障案例
- `knowledge-base/fault-cases/network-deploy-faults.md` — 网络/部署相关故障案例
- `knowledge-base/fault-cases/hardware-module-faults.md` — 硬件模块（制冰机/咖啡机等）故障案例
- `tests/conftest.py` — 共享 fixtures
- `tests/test_diagnosis_report.py` — 诊断报告工具测试
- `tests/test_log_reader.py` — 日志读取工具测试
- `tests/test_device_status.py` — 设备状态查询工具测试
- `tests/test_knowledge_search.py` — 知识库搜索工具测试
- `tests/test_llm_client.py` — LLM 客户端测试
- `tests/test_rag_loader.py` — 文档加载器测试
- `tests/test_rag_splitter.py` — 文本切分器测试
- `tests/test_session_store.py` — 会话管理测试
- `tests/test_api_routes.py` — API 路由集成测试

---

## Task 1: 清理 log_reader.py 重复代码

**Files:**
- Modify: `src/tools/log_reader.py:164-277`

- [ ] **Step 1: 删除重复的函数定义**

删除 `src/tools/log_reader.py` 第 162 行（空行）到第 278 行（文件末尾）的所有内容。保留第 1-161 行（包含正确的 `_read_local`、`_read_ssh`、`fetch_device_logs` 定义）。

要删除的内容是：
- 第 164-207 行：重复的 `_read_local()` — 缺少 `raw_path = LOG_PATHS.get(log_type)` 的安全检查
- 第 210-250 行：重复的 `_read_ssh()` — 使用 `f"grep -i '{keyword}'"` 直接拼接，有注入风险（保留的版本使用 `re.escape(keyword)`）
- 第 253-277 行：重复的 `@tool fetch_device_logs()` — 缺少 `lines` 范围校验和 `_validate_keyword` 调用

保留的版本（行 34-160）更安全更完整：
- `_read_local()` 用 `LOG_PATHS.get(log_type)` 安全获取路径
- `_read_ssh()` 用 `re.escape(keyword)` 防注入
- `fetch_device_logs()` 有完整的参数校验

- [ ] **Step 2: 验证文件正确性**

Run: `python -c "from src.tools.log_reader import fetch_device_logs; print(f'Tool loaded: {fetch_device_logs.name}')"`
Expected: `Tool loaded: fetch_device_logs`

- [ ] **Step 3: Commit**

```bash
git add src/tools/log_reader.py
git commit -m "fix: remove duplicate function definitions in log_reader.py

The file had _read_local, _read_ssh, and fetch_device_logs defined twice.
Kept the first set (lines 34-160) which has better security (re.escape)
and complete parameter validation (lines range check, keyword whitelist)."
```

---

## Task 2: 填充故障案例知识库

**Files:**
- Create: `knowledge-base/fault-cases/middleware-faults.md`
- Create: `knowledge-base/fault-cases/robot-arm-faults.md`
- Create: `knowledge-base/fault-cases/material-monitor-faults.md`
- Create: `knowledge-base/fault-cases/network-deploy-faults.md`
- Create: `knowledge-base/fault-cases/hardware-module-faults.md`

- [ ] **Step 1: 创建中间件故障案例文件**

创建 `knowledge-base/fault-cases/middleware-faults.md`，包含 5-6 个中间件相关故障案例。每个案例格式：

```markdown
# 中间件（bar_middleware）故障案例

## 案例 1：中间件服务启动失败

### 故障现象
设备开机后，点餐屏显示"设备初始化中"持续超过 5 分钟，无法进入正常工作状态。
通过 SSH 登录设备后发现 bar_middleware 进程不存在。

### 涉及模块
bar_middleware（FastAPI 服务，端口 8003）

### 关键日志
```
2024-03-15 08:30:12 ERROR [uvicorn] Application startup failed
2024-03-15 08:30:12 ERROR [bar_middleware] Port 8003 already in use
2024-03-15 08:30:12 ERROR [bar_middleware] Failed to bind socket
```

### 故障原因
上次服务异常退出后端口未释放，或其他进程占用了 8003 端口。

### 解决方案
1. 执行 `lsof -i :8003` 查看占用端口的进程
2. 执行 `kill -9 <PID>` 终止占用进程
3. 执行 `systemctl restart bar_middleware` 重启服务
4. 验证：`curl http://localhost:8003/mid/version` 确认服务正常

### 预防措施
- 配置 systemd 的 Restart=always 实现进程守护
- 在启动脚本中添加端口检查逻辑
```

每个案例文件包含 5-6 个类似结构的真实场景案例。

- [ ] **Step 2: 创建机械臂故障案例文件**

创建 `knowledge-base/fault-cases/robot-arm-faults.md`，包含 5 个机械臂相关故障案例：
- 机械臂归零失败
- 手爪抓取检测异常
- 机械臂运动超时
- 机械臂通信断开
- 手爪物体掉落

- [ ] **Step 3: 创建物料监控故障案例文件**

创建 `knowledge-base/fault-cases/material-monitor-faults.md`，包含 4 个物料监控相关故障案例：
- 物料余量误报
- 通道传感器失灵
- 物料补充未更新
- 物料过期未告警

- [ ] **Step 4: 创建网络/部署故障案例文件**

创建 `knowledge-base/fault-cases/network-deploy-faults.md`，包含 5 个网络和部署相关故障案例：
- OTA 升级失败
- 版本同步不一致
- SSH 连接超时
- Docker 容器重启循环
- 视频内容下发失败

- [ ] **Step 5: 创建硬件模块故障案例文件**

创建 `knowledge-base/fault-cases/hardware-module-faults.md`，包含 5 个硬件模块相关故障案例：
- 制冰机不出冰
- 咖啡机温度异常
- 杯子机卡杯
- 扣盖机对位失败
- 冷凝器温度过高

- [ ] **Step 6: 验证文件可被加载**

```bash
python -c "
from src.rag.loader import load_directory
docs = load_directory('knowledge-base/fault-cases')
print(f'加载 {len(docs)} 个故障案例文档')
assert len(docs) == 5, f'Expected 5, got {len(docs)}'
print('✅ 故障案例加载成功')
"
```

- [ ] **Step 7: Commit**

```bash
git add knowledge-base/fault-cases/
git commit -m "feat: add 25 simulated fault cases across 5 categories

Categories: middleware, robot arm, material monitoring,
network/deploy, and hardware modules. Each case includes
symptoms, affected modules, key logs, root cause, and solutions."
```

---

## Task 3: 创建测试基础设施

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 创建 tests/__init__.py**

创建空文件 `tests/__init__.py`。

- [ ] **Step 2: 创建 conftest.py 共享 fixtures**

创建 `tests/conftest.py`：

```python
"""测试共享 fixtures"""
import os
import pytest
from unittest.mock import MagicMock, patch

# 在导入项目代码之前设置测试环境变量
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_BASE_URL", "")
os.environ.setdefault("OPENAI_BASE_URL", "")
os.environ.setdefault("DEFAULT_LLM_PROVIDER", "claude")
os.environ.setdefault("LOG_READ_MODE", "local")
os.environ.setdefault("VECTOR_DB_TYPE", "chromadb")
os.environ.setdefault("CHROMA_PERSIST_DIR", "./test_chroma_data")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("LLM_FALLBACK_ENABLED", "false")
os.environ.setdefault("MIDDLEWARE_BASE_URL", "http://localhost:8003")


@pytest.fixture
def mock_llm():
    """Mock LLM 实例，返回固定响应"""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="这是一个测试回复")
    llm.stream.return_value = [MagicMock(content="测试"), MagicMock(content="回复")]
    llm.with_fallbacks.return_value = llm
    return llm


@pytest.fixture
def sample_documents():
    """测试用文档列表"""
    from langchain_core.documents import Document
    return [
        Document(
            page_content="# 中间件说明\n\n## 概述\n\nbar_middleware 是饮吧设备的核心中间件。\n\n## 接口\n\n提供 RESTful API。",
            metadata={"source": "test.md", "filename": "test.md", "file_type": "markdown"},
        ),
        Document(
            page_content="制冰机操作手册，包含日常维护和故障排查步骤。",
            metadata={"source": "ice.txt", "filename": "ice.txt", "file_type": "text"},
        ),
    ]


@pytest.fixture
def tmp_log_file(tmp_path):
    """创建临时日志文件"""
    log_file = tmp_path / "test.log"
    log_file.write_text(
        "2024-01-01 INFO 系统启动\n"
        "2024-01-01 ERROR 连接失败\n"
        "2024-01-01 WARN 温度偏高\n"
        "2024-01-01 INFO 任务完成\n"
        "2024-01-01 ERROR 超时错误\n",
        encoding="utf-8",
    )
    return log_file


@pytest.fixture
def tmp_markdown_file(tmp_path):
    """创建临时 Markdown 文件"""
    md_file = tmp_path / "test_doc.md"
    md_file.write_text(
        "# 标题一\n\n内容一\n\n## 标题二\n\n内容二\n\n### 标题三\n\n内容三\n",
        encoding="utf-8",
    )
    return md_file
```

- [ ] **Step 3: 验证 pytest 能发现测试目录**

Run: `python -m pytest tests/ --collect-only 2>&1 | head -5`
Expected: 输出显示 `no tests ran` 或 `collected 0 items`（因为还没写测试）

- [ ] **Step 4: Commit**

```bash
git add tests/__init__.py tests/conftest.py
git commit -m "test: add test infrastructure with shared fixtures

Setup pytest conftest with mock LLM, sample documents,
temporary log/markdown files, and test environment variables."
```

---

## Task 4: 测试诊断报告工具

**Files:**
- Create: `tests/test_diagnosis_report.py`

- [ ] **Step 1: 编写诊断报告工具测试**

创建 `tests/test_diagnosis_report.py`：

```python
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
        assert "无" in result

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
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/test_diagnosis_report.py -v`
Expected: 6 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_diagnosis_report.py
git commit -m "test: add diagnosis report tool tests (6 cases)

Tests cover basic report, all fields, defaults, empty optionals,
timestamp, and report structure validation."
```

---

## Task 5: 测试日志读取工具

**Files:**
- Create: `tests/test_log_reader.py`

- [ ] **Step 1: 编写日志读取工具测试**

创建 `tests/test_log_reader.py`：

```python
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
            # 不应包含 INFO 行
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
        mock_result = MagicMock(
            stdout="log line 1\nlog line 2",
            stderr="",
            returncode=0,
        )
        with patch("src.tools.log_reader.subprocess.run", return_value=mock_result):
            result = _read_ssh("syslog", 50, "")
            assert "设备日志 - syslog" in result
            assert "log line 1" in result

    def test_ssh_connection_refused(self):
        """SSH 连接被拒绝"""
        mock_result = MagicMock(
            stdout="",
            stderr="Connection refused",
            returncode=1,
        )
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
        with patch(
            "src.tools.log_reader.subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            result = _read_ssh("syslog", 50, "")
            assert "SSH 客户端未找到" in result

    def test_ssh_with_keyword(self):
        """SSH 模式带关键词"""
        mock_result = MagicMock(stdout="error line", stderr="", returncode=0)
        with patch("src.tools.log_reader.subprocess.run", return_value=mock_result) as mock_run:
            result = _read_ssh("syslog", 50, "error")
            assert "过滤: 'error'" in result
            # 验证命令中使用了 re.escape
            call_args = mock_run.call_args[0][0]
            ssh_command = call_args[-1]
            assert "grep" in ssh_command


class TestFetchDeviceLogs:
    """fetch_device_logs 工具入口"""

    def test_invalid_log_type(self):
        """不支持的日志类型"""
        result = fetch_device_logs.invoke({
            "log_type": "invalid",
            "lines": 50,
            "keyword": "",
        })
        assert "不支持的日志类型" in result

    def test_lines_out_of_range(self):
        """lines 超出范围"""
        result = fetch_device_logs.invoke({
            "log_type": "syslog",
            "lines": 0,
            "keyword": "",
        })
        assert "1-1000" in result

        result = fetch_device_logs.invoke({
            "log_type": "syslog",
            "lines": 1001,
            "keyword": "",
        })
        assert "1-1000" in result

    def test_invalid_keyword(self):
        """非法关键词"""
        result = fetch_device_logs.invoke({
            "log_type": "syslog",
            "lines": 50,
            "keyword": "$(rm -rf /)",
        })
        assert "非法字符" in result

    def test_dispatch_to_local(self, tmp_log_file):
        """local 模式分发到 _read_local"""
        with patch.dict(LOG_PATHS, {"syslog": str(tmp_log_file)}):
            with patch("src.tools.log_reader.settings") as mock_settings:
                mock_settings.LOG_READ_MODE = "local"
                result = fetch_device_logs.invoke({
                    "log_type": "syslog",
                    "lines": 50,
                    "keyword": "",
                })
                assert "设备日志" in result

    def test_dispatch_to_ssh(self):
        """ssh 模式分发到 _read_ssh"""
        mock_result = MagicMock(stdout="ssh log", stderr="", returncode=0)
        with patch("src.tools.log_reader.settings") as mock_settings:
            mock_settings.LOG_READ_MODE = "ssh"
            mock_settings.DEVICE_SSH_USER = "test"
            mock_settings.DEVICE_SSH_HOST = "1.2.3.4"
            with patch("src.tools.log_reader.subprocess.run", return_value=mock_result):
                result = fetch_device_logs.invoke({
                    "log_type": "syslog",
                    "lines": 50,
                    "keyword": "",
                })
                assert "设备日志" in result
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/test_log_reader.py -v`
Expected: 16 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_log_reader.py
git commit -m "test: add log reader tool tests (16 cases)

Tests cover keyword validation, local file reading (with/without
keyword filter, docker mode), SSH reading (success, connection refused,
timeout, not found), and fetch_device_logs entry point dispatching."
```

---

## Task 6: 测试设备状态查询工具

**Files:**
- Create: `tests/test_device_status.py`

- [ ] **Step 1: 编写设备状态工具测试**

创建 `tests/test_device_status.py`：

```python
"""测试：query_device_status 工具"""
from unittest.mock import patch, MagicMock
from src.tools.device_status import (
    _fetch,
    _format_module_status,
    query_device_status,
    MODULE_STATUS_ENDPOINTS,
    SPECIAL_ENDPOINTS,
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
        """接口无响应"""
        result = _format_module_status("制冰机", None)
        assert "接口无响应" in result

    def test_not_success(self):
        """请求成功但业务失败"""
        data = {"success": False, "msg": "设备离线"}
        result = _format_module_status("制冰机", data)
        assert "设备离线" in result

    def test_status_list_format(self):
        """标准 status_list 格式"""
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
        """status_list 中有错误码"""
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
        """不支持的模块名"""
        result = query_device_status.invoke({"module": "不存在的模块"})
        assert "不支持的模块" in result

    def test_single_module_query(self):
        """查询单个标准模块"""
        mock_data = {"success": True, "data": {"status_list": [{"name": "冰块仓", "status": "normal"}]}}
        with patch("src.tools.device_status._fetch", return_value=mock_data):
            result = query_device_status.invoke({"module": "制冰机"})
            assert "制冰机" in result
            assert "normal" in result

    def test_robot_arm_query(self):
        """查询机械臂（特殊格式）"""
        mock_data = {"success": True, "msg": "空闲"}
        with patch("src.tools.device_status._fetch", return_value=mock_data):
            result = query_device_status.invoke({"module": "机械臂"})
            assert "机械臂" in result

    def test_middleware_version_query(self):
        """查询中间件版本"""
        mock_data = {"version": "2.1.0"}
        with patch("src.tools.device_status._fetch", return_value=mock_data):
            result = query_device_status.invoke({"module": "中间件版本"})
            assert "2.1.0" in result

    def test_all_modules_middleware_offline(self):
        """查询全部但中间件离线"""
        with patch("src.tools.device_status._fetch", return_value=None):
            result = query_device_status.invoke({"module": "all"})
            assert "无法连接" in result

    def test_all_modules_success(self):
        """查询全部模块"""
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
            assert "硬件模块状态" in result
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/test_device_status.py -v`
Expected: 10 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_device_status.py
git commit -m "test: add device status query tool tests (10 cases)

Tests cover HTTP fetch, status formatting (null/error/status_list),
single module queries (standard/robot arm/middleware version),
and full status overview (online/offline scenarios)."
```

---

## Task 7: 测试知识库搜索工具

**Files:**
- Create: `tests/test_knowledge_search.py`

- [ ] **Step 1: 编写知识库搜索工具测试**

创建 `tests/test_knowledge_search.py`：

```python
"""测试：search_knowledge_base 工具"""
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from src.tools.knowledge_search import search_knowledge_base


class TestSearchKnowledgeBase:

    def test_no_results(self):
        """检索无结果"""
        with patch("src.tools.knowledge_search.search_with_scores", return_value=[]):
            result = search_knowledge_base.invoke({"query": "不存在的内容"})
            assert "没有找到" in result

    def test_results_with_headers(self):
        """检索结果包含标题层级"""
        doc = Document(
            page_content="制冰机需要定期除霜维护",
            metadata={"filename": "ice-manual.md", "h1": "设备维护", "h2": "制冰机"},
        )
        with patch("src.tools.knowledge_search.search_with_scores", return_value=[(doc, 0.85)]):
            result = search_knowledge_base.invoke({"query": "制冰机维护"})
            assert "ice-manual.md" in result
            assert "设备维护 > 制冰机" in result
            assert "制冰机需要定期除霜维护" in result

    def test_results_without_headers(self):
        """检索结果没有标题信息"""
        doc = Document(
            page_content="操作说明内容",
            metadata={"filename": "guide.pdf"},
        )
        with patch("src.tools.knowledge_search.search_with_scores", return_value=[(doc, 0.7)]):
            result = search_knowledge_base.invoke({"query": "操作说明"})
            assert "guide.pdf" in result
            assert "操作说明内容" in result

    def test_multiple_results(self):
        """多个检索结果"""
        docs = [
            (Document(page_content=f"文档内容 {i}", metadata={"filename": f"doc{i}.md"}), 0.9 - i * 0.1)
            for i in range(3)
        ]
        with patch("src.tools.knowledge_search.search_with_scores", return_value=docs):
            result = search_knowledge_base.invoke({"query": "搜索"})
            assert "[1]" in result
            assert "[2]" in result
            assert "[3]" in result
            assert "doc0.md" in result
            assert "doc2.md" in result

    def test_content_truncation(self):
        """长内容截断到 500 字符"""
        long_content = "A" * 1000
        doc = Document(page_content=long_content, metadata={"filename": "long.md"})
        with patch("src.tools.knowledge_search.search_with_scores", return_value=[(doc, 0.5)]):
            result = search_knowledge_base.invoke({"query": "test"})
            # 内容应该被截断到 500 字符
            assert len(result.split("long.md")[1]) < 600
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/test_knowledge_search.py -v`
Expected: 5 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_knowledge_search.py
git commit -m "test: add knowledge search tool tests (5 cases)

Tests cover no results, results with/without markdown headers,
multiple results ordering, and content truncation."
```

---

## Task 8: 测试 LLM 客户端

**Files:**
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: 编写 LLM 客户端测试**

创建 `tests/test_llm_client.py`：

```python
"""测试：LLM 客户端（多模型切换、降级、文本提取）"""
from unittest.mock import patch, MagicMock
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.llm.client import (
    _create_single_llm,
    _get_fallback_provider,
    create_llm,
    extract_text,
    DiagnosticChat,
    DIAGNOSTIC_SYSTEM_PROMPT,
)


class TestExtractText:
    """文本提取（处理 extended thinking 格式）"""

    def test_string_content(self):
        assert extract_text("hello") == "hello"

    def test_list_content_with_text_blocks(self):
        content = [
            {"type": "thinking", "text": "思考中..."},
            {"type": "text", "text": "最终回答"},
        ]
        assert extract_text(content) == "最终回答"

    def test_list_multiple_text_blocks(self):
        content = [
            {"type": "text", "text": "部分1"},
            {"type": "text", "text": "部分2"},
        ]
        assert extract_text(content) == "部分1部分2"

    def test_empty_list(self):
        assert extract_text([]) == ""

    def test_other_types(self):
        assert extract_text(123) == "123"


class TestCreateSingleLLM:
    """单 provider LLM 创建"""

    def test_create_claude(self):
        with patch("src.llm.client.ChatAnthropic") as mock_cls:
            _create_single_llm("claude")
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args[1]
            assert "api_key" in call_kwargs
            assert "model" in call_kwargs

    def test_create_openai(self):
        with patch("src.llm.client.ChatOpenAI") as mock_cls:
            _create_single_llm("openai")
            mock_cls.assert_called_once()

    def test_unsupported_provider(self):
        import pytest
        with pytest.raises(ValueError, match="不支持"):
            _create_single_llm("gemini")


class TestGetFallbackProvider:
    """降级 provider 查找"""

    def test_claude_fallback_to_openai(self):
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "key"
            assert _get_fallback_provider("claude") == "openai"

    def test_openai_fallback_to_claude(self):
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "key"
            assert _get_fallback_provider("openai") == "claude"

    def test_no_fallback_without_key(self):
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            assert _get_fallback_provider("claude") is None


class TestCreateLLM:
    """create_llm 工厂函数"""

    def test_no_fallback_when_disabled(self):
        with patch("src.llm.client._create_single_llm") as mock_create:
            mock_llm = MagicMock()
            mock_create.return_value = mock_llm
            with patch("src.llm.client.settings") as mock_settings:
                mock_settings.DEFAULT_LLM_PROVIDER = "claude"
                mock_settings.LLM_FALLBACK_ENABLED = False
                result = create_llm()
                assert result == mock_llm
                mock_llm.with_fallbacks.assert_not_called()

    def test_fallback_chain_when_enabled(self):
        primary = MagicMock()
        fallback = MagicMock()
        chained = MagicMock()
        primary.with_fallbacks.return_value = chained

        with patch("src.llm.client._create_single_llm", side_effect=[primary, fallback]):
            with patch("src.llm.client.settings") as mock_settings:
                mock_settings.DEFAULT_LLM_PROVIDER = "claude"
                mock_settings.LLM_FALLBACK_ENABLED = True
                with patch("src.llm.client._get_fallback_provider", return_value="openai"):
                    result = create_llm()
                    primary.with_fallbacks.assert_called_once_with([fallback])
                    assert result == chained


class TestDiagnosticChat:
    """DiagnosticChat 对话管理器"""

    def test_init(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = DiagnosticChat("claude")
            assert len(chat.history) == 1
            assert isinstance(chat.history[0], SystemMessage)
            assert chat.provider_name == "claude"

    def test_chat(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = DiagnosticChat("claude")
            result = chat.chat("你好")
            assert result == "这是一个测试回复"
            assert len(chat.history) == 3  # system + human + ai
            assert isinstance(chat.history[1], HumanMessage)
            assert isinstance(chat.history[2], AIMessage)

    def test_clear_history(self, mock_llm):
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = DiagnosticChat("claude")
            chat.chat("你好")
            assert len(chat.history) == 3
            chat.clear_history()
            assert len(chat.history) == 1
            assert isinstance(chat.history[0], SystemMessage)

    def test_switch_model(self, mock_llm):
        new_llm = MagicMock()
        with patch("src.llm.client.create_llm", side_effect=[mock_llm, new_llm]):
            chat = DiagnosticChat("claude")
            chat.switch_model("openai")
            assert chat.provider_name == "openai"
            assert chat.llm == new_llm

    def test_stream_chat(self, mock_llm):
        """流式对话"""
        mock_llm.stream.return_value = [
            MagicMock(content="你"),
            MagicMock(content="好"),
        ]
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = DiagnosticChat("claude")
            tokens = list(chat.stream_chat("测试"))
            assert tokens == ["你", "好"]
            # history 应该被更新
            assert len(chat.history) == 3
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/test_llm_client.py -v`
Expected: 16 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_llm_client.py
git commit -m "test: add LLM client tests (16 cases)

Tests cover extract_text (extended thinking format), provider creation
(claude/openai/unsupported), fallback logic (enable/disable/no-key),
and DiagnosticChat (chat/stream/clear/switch)."
```

---

## Task 9: 测试 RAG 加载器和切分器

**Files:**
- Create: `tests/test_rag_loader.py`
- Create: `tests/test_rag_splitter.py`

- [ ] **Step 1: 编写文档加载器测试**

创建 `tests/test_rag_loader.py`：

```python
"""测试：文档加载器"""
from pathlib import Path
from langchain_core.documents import Document
from src.rag.loader import load_markdown, load_pdf, load_directory


class TestLoadMarkdown:

    def test_load_markdown_file(self, tmp_markdown_file):
        docs = load_markdown(str(tmp_markdown_file))
        assert len(docs) == 1
        assert "标题一" in docs[0].page_content
        assert docs[0].metadata["file_type"] == "markdown"
        assert docs[0].metadata["filename"] == "test_doc.md"

    def test_load_markdown_metadata(self, tmp_markdown_file):
        docs = load_markdown(str(tmp_markdown_file))
        assert "source" in docs[0].metadata
        assert "filename" in docs[0].metadata


class TestLoadDirectory:

    def test_load_directory_mixed(self, tmp_path):
        """加载包含多种格式的目录"""
        (tmp_path / "doc1.md").write_text("# Markdown 文档\n\n内容", encoding="utf-8")
        (tmp_path / "doc2.txt").write_text("纯文本文档", encoding="utf-8")
        (tmp_path / "ignore.json").write_text("{}", encoding="utf-8")  # 应忽略

        docs = load_directory(str(tmp_path))
        assert len(docs) == 2  # md + txt, 忽略 json

    def test_load_empty_directory(self, tmp_path):
        """空目录"""
        docs = load_directory(str(tmp_path))
        assert len(docs) == 0

    def test_load_subdirectory(self, tmp_path):
        """递归加载子目录"""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.md").write_text("# 嵌套文档", encoding="utf-8")

        docs = load_directory(str(tmp_path))
        assert len(docs) == 1
        assert "嵌套文档" in docs[0].page_content
```

- [ ] **Step 2: 编写文本切分器测试**

创建 `tests/test_rag_splitter.py`：

```python
"""测试：文本切分器"""
from langchain_core.documents import Document
from src.rag.splitter import create_text_splitter, create_markdown_splitter, split_documents


class TestCreateTextSplitter:

    def test_default_params(self):
        splitter = create_text_splitter()
        assert splitter._chunk_size == 1000
        assert splitter._chunk_overlap == 200

    def test_custom_params(self):
        splitter = create_text_splitter(chunk_size=500, chunk_overlap=50)
        assert splitter._chunk_size == 500
        assert splitter._chunk_overlap == 50


class TestCreateMarkdownSplitter:

    def test_split_by_headers(self):
        splitter = create_markdown_splitter()
        text = "# 标题\n\n内容一\n\n## 子标题\n\n内容二"
        chunks = splitter.split_text(text)
        assert len(chunks) >= 1


class TestSplitDocuments:

    def test_split_markdown_doc(self):
        """Markdown 文档二次切分"""
        doc = Document(
            page_content="# 标题\n\n内容段落一。\n\n## 子标题\n\n内容段落二。",
            metadata={"source": "test.md", "filename": "test.md", "file_type": "markdown"},
        )
        chunks = split_documents([doc], chunk_size=100, chunk_overlap=20)
        assert len(chunks) >= 1
        # 检查 metadata 被保留
        for chunk in chunks:
            assert chunk.metadata["filename"] == "test.md"

    def test_split_text_doc(self):
        """非 Markdown 文档直接切分"""
        doc = Document(
            page_content="这是一段很长的文本。" * 100,
            metadata={"source": "test.txt", "filename": "test.txt", "file_type": "text"},
        )
        chunks = split_documents([doc], chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1

    def test_short_doc_no_split(self):
        """短文档不需要切分"""
        doc = Document(
            page_content="很短的文档",
            metadata={"source": "short.txt", "filename": "short.txt", "file_type": "text"},
        )
        chunks = split_documents([doc], chunk_size=1000, chunk_overlap=200)
        assert len(chunks) == 1

    def test_markdown_headers_in_metadata(self):
        """Markdown 切分后标题信息在 metadata 中"""
        doc = Document(
            page_content="# 一级标题\n\n内容\n\n## 二级标题\n\n更多内容",
            metadata={"source": "test.md", "filename": "test.md", "file_type": "markdown"},
        )
        chunks = split_documents([doc], chunk_size=1000, chunk_overlap=200)
        # 至少一个 chunk 应有标题 metadata
        has_header = any("h1" in c.metadata or "h2" in c.metadata for c in chunks)
        assert has_header
```

- [ ] **Step 3: 运行测试确认通过**

Run: `python -m pytest tests/test_rag_loader.py tests/test_rag_splitter.py -v`
Expected: 11 tests PASSED

- [ ] **Step 4: Commit**

```bash
git add tests/test_rag_loader.py tests/test_rag_splitter.py
git commit -m "test: add RAG loader and splitter tests (11 cases)

Loader tests: markdown loading, directory scanning (mixed formats,
empty, subdirectory). Splitter tests: text splitter params,
markdown header splitting, two-stage splitting, metadata preservation."
```

---

## Task 10: 测试会话管理

**Files:**
- Create: `tests/test_session_store.py`

- [ ] **Step 1: 编写会话管理测试**

创建 `tests/test_session_store.py`：

```python
"""测试：会话管理（MemorySessionStore + 序列化/反序列化）"""
import json
from unittest.mock import patch, MagicMock
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.utils.session_store import (
    _serialize_session,
    _deserialize_session,
    MemorySessionStore,
    create_session_store,
)


class TestSerializeSession:

    def test_serialize_roundtrip(self, mock_llm):
        """序列化 → 反序列化 round-trip"""
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            from src.llm.client import DiagnosticChat
            chat = DiagnosticChat("claude")
            chat.history.append(HumanMessage(content="你好"))
            chat.history.append(AIMessage(content="你好！"))

            raw = _serialize_session(chat)
            data = json.loads(raw)
            assert data["provider"] == "claude"
            assert len(data["messages"]) == 3  # system + human + ai

    def test_deserialize_new_format(self, mock_llm):
        """反序列化新格式（含 provider）"""
        raw = json.dumps({
            "provider": "openai",
            "messages": [
                {"type": "system", "content": "系统提示"},
                {"type": "human", "content": "你好"},
            ]
        })
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = _deserialize_session(raw, "claude")
            assert len(chat.history) == 2
            assert isinstance(chat.history[0], SystemMessage)
            assert isinstance(chat.history[1], HumanMessage)

    def test_deserialize_legacy_format(self, mock_llm):
        """反序列化旧格式（纯消息列表）"""
        raw = json.dumps([
            {"type": "system", "content": "旧系统提示"},
            {"type": "human", "content": "旧消息"},
        ])
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            chat = _deserialize_session(raw, "claude")
            assert len(chat.history) == 2


class TestMemorySessionStore:

    def test_get_creates_new_session(self, mock_llm):
        """获取不存在的会话会创建新的"""
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            store = MemorySessionStore()
            chat = store.get("session-1", "claude")
            assert chat is not None
            assert chat.provider_name == "claude"

    def test_get_returns_same_session(self, mock_llm):
        """同一 session_id 返回同一对象"""
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            store = MemorySessionStore()
            chat1 = store.get("session-1", "claude")
            chat2 = store.get("session-1", "claude")
            assert chat1 is chat2

    def test_delete_existing(self, mock_llm):
        """删除存在的会话"""
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            store = MemorySessionStore()
            store.get("session-1", "claude")
            assert store.delete("session-1") is True
            assert store.delete("session-1") is False

    def test_list_sessions(self, mock_llm):
        """列出所有会话"""
        with patch("src.llm.client.create_llm", return_value=mock_llm):
            store = MemorySessionStore()
            store.get("s1", "claude")
            store.get("s2", "openai")
            sessions = store.list_sessions()
            assert len(sessions) == 2
            ids = {s["id"] for s in sessions}
            assert ids == {"s1", "s2"}


class TestCreateSessionStore:

    def test_fallback_to_memory(self):
        """Redis 不可用时降级到内存"""
        with patch("src.utils.session_store.settings") as mock_settings:
            mock_settings.REDIS_URL = ""
            store = create_session_store()
            assert isinstance(store, MemorySessionStore)

    def test_redis_connection_failure(self):
        """Redis 连接失败降级到内存"""
        with patch("src.utils.session_store.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            with patch("src.utils.session_store.RedisSessionStore", side_effect=Exception("Connection refused")):
                store = create_session_store()
                assert isinstance(store, MemorySessionStore)
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/test_session_store.py -v`
Expected: 9 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_session_store.py
git commit -m "test: add session store tests (9 cases)

Tests cover serialization round-trip, deserialization (new/legacy format),
MemorySessionStore (create/get/delete/list), and create_session_store
fallback logic (no Redis URL, connection failure)."
```

---

## Task 11: 测试 API 路由（集成测试）

**Files:**
- Create: `tests/test_api_routes.py`

- [ ] **Step 1: 编写 API 路由集成测试**

创建 `tests/test_api_routes.py`：

```python
"""测试：API 路由（集成测试，使用 FastAPI TestClient）"""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from src.api.app import app
from src.utils.session_store import MemorySessionStore


@pytest.fixture
def mock_store(mock_llm):
    """Mock 会话存储"""
    with patch("src.llm.client.create_llm", return_value=mock_llm):
        store = MemorySessionStore()
        with patch("src.api.routes._store", store):
            yield store


@pytest.fixture
async def client():
    """异步测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "ai-diagnostic-agent"


class TestChatEndpoint:

    @pytest.mark.asyncio
    async def test_chat_success(self, client, mock_store):
        response = await client.post("/api/chat", json={
            "message": "你好",
            "provider": "claude",
            "session_id": "test-session",
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_chat_missing_message(self, client):
        response = await client.post("/api/chat", json={
            "provider": "claude",
        })
        assert response.status_code == 422  # Pydantic 校验失败


class TestRAGEndpoint:

    @pytest.mark.asyncio
    async def test_rag_query(self, client):
        mock_result = {
            "answer": "测试回答",
            "sources": ["doc1.md"],
            "context_count": 1,
        }
        with patch("src.api.routes.rag_query", return_value=mock_result):
            response = await client.post("/api/rag/query", json={
                "query": "制冰机故障",
                "top_k": 3,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "测试回答"
            assert data["sources"] == ["doc1.md"]


class TestSessionEndpoints:

    @pytest.mark.asyncio
    async def test_list_sessions(self, client, mock_store):
        response = await client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, client, mock_store):
        response = await client.delete("/api/session/nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert "不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_delete_session_exists(self, client, mock_store):
        # 先创建会话
        await client.post("/api/chat", json={
            "message": "创建会话",
            "session_id": "to-delete",
        })
        response = await client.delete("/api/session/to-delete")
        assert response.status_code == 200
        data = response.json()
        assert "已清除" in data["message"]


class TestDiagnoseEndpoint:

    @pytest.mark.asyncio
    async def test_diagnose(self, client):
        """Agent 诊断端点"""
        mock_ai_msg = MagicMock()
        mock_ai_msg.__class__.__name__ = "AIMessage"
        mock_ai_msg.content = "诊断结论：设备正常"
        mock_ai_msg.tool_calls = []

        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [mock_ai_msg]}

        with patch("src.api.routes.create_diagnostic_agent", return_value=mock_agent):
            response = await client.post("/api/diagnose", json={
                "question": "制冰机不工作",
                "provider": "claude",
            })
            assert response.status_code == 200
            data = response.json()
            assert "result" in data
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/test_api_routes.py -v`
Expected: 7 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_api_routes.py
git commit -m "test: add API route integration tests (7 cases)

Tests cover health endpoint, chat (success/validation error),
RAG query, session management (list/delete), and diagnose endpoint.
Uses httpx AsyncClient with FastAPI ASGITransport."
```

---

## Task 12: 运行全部测试并确认覆盖率

- [ ] **Step 1: 运行全部测试**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASSED (约 80 个测试用例)

- [ ] **Step 2: 确认所有测试通过后做最终 commit**

```bash
git add -A
git commit -m "feat: complete iteration 1 - quality foundation

Summary:
- Fixed duplicate function definitions in log_reader.py
- Added 25 fault cases across 5 categories to knowledge base
- Built comprehensive test suite: 80+ tests covering all modules
  - Tools: diagnosis_report, log_reader, device_status, knowledge_search
  - LLM client: extract_text, provider creation, fallback, DiagnosticChat
  - RAG: document loader, text splitter
  - Session store: serialize/deserialize, memory store, fallback
  - API routes: all 7 endpoints (integration tests)"
```
