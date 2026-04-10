# 硬件模块自动化测试服务使用手册（SOP）

## 1. 适用对象

本文档面向测试使用者，说明如何在不关注程序内部实现细节的前提下，使用本系统完成一次自动化测试任务。

适用场景：

- 已经在目标 Linux 主机部署好 `hardware-module-test-service`
- `bar_middleware` 已正常启动
- 已准备好测试配置文件

## 2. 使用目标

测试使用者通过本系统可以完成以下操作：

- 启动一次测试任务
- 查询当前测试运行状态和进度
- 在需要时暂停测试
- 获取 JSON/HTML 测试报告
- 查询历史报告列表

## 3. 系统架构简述

```text
┌──────────────────────────────────────────────────────────┐
│                    Linux 主机 (192.168.42.1)              │
│                                                          │
│  ┌─────────────────────────────┐                         │
│  │  bar_middleware (Docker)    │  ← 控制硬件设备          │
│  │  端口: 8003                 │    (机械臂/杯机/盖机等)  │
│  │  systemd: bar-middleware    │                         │
│  └──────────────▲──────────────┘                         │
│                 │ HTTP 调用                               │
│  ┌──────────────┴──────────────┐                         │
│  │  hardware-module-test-      │  ← 测试调度服务          │
│  │  service (Python/FastAPI)   │    (读取配置/执行流程/   │
│  │  端口: 18080                │     生成报告)            │
│  │  systemd: hardware-module-  │                         │
│  │           test-service      │                         │
│  └─────────────────────────────┘                         │
└──────────────────────────────────────────────────────────┘
         ▲
         │ HTTP 接口 / Swagger UI
         │
    测试使用者（浏览器 / Apifox / curl）
```

两个服务均已配置为 systemd 开机自启，主机重启后无需手动操作。

## 4. 使用前准备

在开始测试前，请确认以下事项：

### 4.1 确认服务已启动

浏览器打开：

```text
http://192.168.42.1:18080/health
```

返回示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "service": "hardware-module-test-service",
    "middleware_base_url": "http://127.0.0.1:8003",
    "simulate_bar_middleware_success": false,
    "simulate_bar_middleware_delay_ms": 0,
    "simulate_bar_middleware_fail_actions": [],
    "simulate_bar_middleware_fail_actions_once": []
  }
}
```

重点确认：

- `success` 为 `true` → 服务正常
- `middleware_base_url` 为 `http://127.0.0.1:8003` → 中间件地址正确
- `simulate_bar_middleware_success` 为 `false` → 非模拟模式，真实控制硬件

如果 `simulate_bar_middleware_success` 为 `true`，说明当前处于模拟模式，所有硬件动作会直接返回成功，不会真正控制设备。

### 4.2 确认 bar_middleware 已启动

如果 `/health` 能正常返回，但启动测试后步骤报超时或连接失败，可能是 `bar_middleware` 未启动。

SSH 登录主机检查：

```bash
# 检查容器状态
docker ps | grep barMiddleware

# 如果没有运行，手动启动
sudo systemctl restart bar-middleware
```

### 4.3 准备测试配置文件

配置文件存放在主机目录：

```text
/home/smyze/test/pydemo/hardware-module-test-service/configs/
```

目前已有的配置文件：

| 文件名 | 说明 |
|--------|------|
| `cold-hot-cup-lid-drop-test.yaml` | 冷热杯扣盖丢杯自动化测试 |
| `example-hot-flow.yaml` | 热杯完整流程测试（含手爪检查） |

配置文件可以随时修改或新增，不需要重启服务。每次启动测试时会实时读取最新内容。

配置文件的详细字段说明请参考 [测试配置文件说明.md](测试配置文件说明.md)。

### 4.4 确认配置文件内容

启动前建议检查：

- 流程顺序是否正确
- 循环次数（`cycles`）是否合理
- 失败策略（`on_failure`）是否符合预期
- 机械臂点位编码（`target_pose`）是否正确
- 杯型（`cup_type`）是否匹配实际杯机
- 是否有流程被 `enabled: false` 禁用了

## 5. 常用地址

服务地址：

```text
http://192.168.42.1:18080
```

| 用途 | 地址 | 方法 |
|------|------|------|
| 健康检查 | `/health` | GET |
| Swagger 文档 | `/docs` | 浏览器打开 |
| 启动测试 | `/api/v1/runs/start` | POST |
| 暂停测试 | `/api/v1/runs/pause` | POST |
| 查询当前运行 | `/api/v1/runs/current` | GET |
| 查询指定运行 | `/api/v1/runs/{run_id}` | GET |
| 查询运行进度 | `/api/v1/runs/{run_id}/progress` | GET |
| 查询报告列表 | `/api/v1/reports` | GET |
| 查询报告详情 | `/api/v1/reports/{run_id}` | GET |
| 下载 JSON 报告 | `/api/v1/reports/{run_id}/download/json` | GET |
| 下载 HTML 报告 | `/api/v1/reports/{run_id}/download/html` | GET |

## 6. 推荐使用方式

### 方式一：Swagger 页面（推荐日常使用）

浏览器打开：

```text
http://192.168.42.1:18080/docs
```

所有接口都可以直接在页面上填参数、点击执行、查看返回结果。

### 方式二：Apifox / Postman

导入 OpenAPI 文档：

```text
http://192.168.42.1:18080/openapi.json
```

详见 [Apifox使用说明.md](Apifox使用说明.md)。

### 方式三：curl 命令行

适合脚本化或远程操作，示例见下方各步骤。

## 7. 标准操作流程

### 步骤 1：确认服务健康

```bash
curl http://192.168.42.1:18080/health
```

确认 `success` 为 `true`，`simulate_bar_middleware_success` 为 `false`。

### 步骤 2：启动测试

Swagger 页面找到 `POST /api/v1/runs/start`，填写：

```json
{
  "config_source_type": "file_path",
  "config_file_path": "/home/smyze/test/pydemo/hardware-module-test-service/configs/cold-hot-cup-lid-drop-test.yaml",
  "operator": "smyze"
}
```

或使用 curl：

```bash
curl -X POST http://192.168.42.1:18080/api/v1/runs/start \
  -H "Content-Type: application/json" \
  -d '{
    "config_source_type": "file_path",
    "config_file_path": "/home/smyze/test/pydemo/hardware-module-test-service/configs/cold-hot-cup-lid-drop-test.yaml",
    "operator": "smyze"
  }'
```

字段说明：

| 字段 | 说明 |
|------|------|
| `config_source_type` | 固定填 `file_path`（也支持 `inline` 直接传 YAML 文本） |
| `config_file_path` | 配置文件在 Linux 主机上的绝对路径（不是你本地电脑的路径） |
| `operator` | 操作人，可选，会记录在报告中 |

启动成功返回示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "run started",
  "data": {
    "run_id": "run_20260407_150000_001",
    "status": "running",
    "job_name": "冷热杯扣盖丢杯自动化测试",
    "started_at": "2026-04-07T15:00:00.123456+08:00"
  }
}
```

返回的 `run_id` 非常重要，后续查询进度、查看报告、下载报告都要用它。

### 步骤 3：查看当前运行状态

```bash
curl http://192.168.42.1:18080/api/v1/runs/current
```

返回当前正在执行的实时快照：

```json
{
  "success": true,
  "data": {
    "run_id": "run_20260407_150000_001",
    "status": "running",
    "job_name": "冷热杯扣盖丢杯自动化测试",
    "current_flow_id": "cold_cup_flow",
    "current_flow_name": "冷杯-接杯扣盖丢杯",
    "current_cycle": 3,
    "total_cycles": 5,
    "current_step_index": 5,
    "current_step_name": "扣盖前检查",
    "current_action": "lid.pre_check"
  }
}
```

适合快速确认系统是否还在正常执行。如果当前没有运行中的任务，会返回 `NO_ACTIVE_RUN`。

### 步骤 4：查看运行进度

```bash
curl http://192.168.42.1:18080/api/v1/runs/{run_id}/progress
```

返回更详细的进度统计：

```json
{
  "success": true,
  "data": {
    "run_id": "run_20260407_150000_001",
    "status": "running",
    "summary": {
      "total_flows": 2,
      "completed_flows": 1,
      "total_steps": 170,
      "completed_steps": 102,
      "success_steps": 100,
      "failed_steps": 1,
      "skipped_steps": 1
    },
    "current": {
      "flow_id": "hot_cup_flow",
      "flow_cycle": 2,
      "step_index": 5,
      "step_name": "扣盖前检查",
      "action": "lid.pre_check",
      "attempt": 1
    }
  }
}
```

这个接口比 `/runs/current` 更适合做进度跟踪，可以看到总步骤数、已完成数、成功/失败/跳过数。

运行结束后也可以用同一个接口查看最终统计。

### 步骤 5：需要时暂停测试

如果测试中途需要停止，调用：

```bash
curl -X POST http://192.168.42.1:18080/api/v1/runs/pause \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "现场需要调整设备",
    "operator": "smyze"
  }'
```

暂停规则：

- 暂停不是立即强杀当前设备动作，会在当前步骤执行完毕后（步骤边界）生效
- 当前运行会结束，状态变为 `paused`
- 系统会输出截至暂停时刻的测试报告
- 如果配置了 `recovery_pose`，机械臂会尝试回到安全点位
- 下次需要重新调用 `start` 从头执行

### 步骤 6：查看测试结果

运行结束后，调用：

```bash
curl http://192.168.42.1:18080/api/v1/reports/{run_id}
```

返回完整的测试报告 JSON，包含所有流程、步骤的执行详情。

重点关注字段：

| 字段 | 说明 |
|------|------|
| `status` | 最终状态：`completed` / `failed` / `paused` |
| `termination_reason` | 结束原因：`all_completed` / `step_failed` / `paused_by_request` / `internal_error` |
| `termination_detail` | 结束原因详情（失败时会包含具体错误信息） |
| `summary` | 执行摘要（成功/失败/跳过步骤数等） |
| `steps` | 所有步骤的执行记录 |
| `flows` | 所有流程的执行记录 |

### 步骤 7：下载报告

下载 JSON 报告（适合存档、程序处理）：

```bash
curl -o report.json http://192.168.42.1:18080/api/v1/reports/{run_id}/download/json
```

下载 HTML 报告（适合直接查看、发给同事）：

```bash
curl -o report.html http://192.168.42.1:18080/api/v1/reports/{run_id}/download/html
```

也可以直接在浏览器打开下载链接：

```text
http://192.168.42.1:18080/api/v1/reports/{run_id}/download/html
```

不需要 SSH 登录主机去找文件。

## 8. 查询历史报告

调用报告列表接口，支持分页和过滤：

```bash
# 查询所有报告（默认第 1 页，每页 20 条）
curl http://192.168.42.1:18080/api/v1/reports

# 按状态过滤
curl "http://192.168.42.1:18080/api/v1/reports?status=failed"

# 按任务名过滤（模糊匹配）
curl "http://192.168.42.1:18080/api/v1/reports?job_name=冷热杯"

# 按时间范围过滤
curl "http://192.168.42.1:18080/api/v1/reports?start_time_from=2026-04-07T00:00:00&start_time_to=2026-04-07T23:59:59"

# 分页
curl "http://192.168.42.1:18080/api/v1/reports?page=2&page_size=10"
```

返回示例：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "run_id": "run_20260407_150000_001",
        "job_name": "冷热杯扣盖丢杯自动化测试",
        "status": "completed",
        "started_at": "2026-04-07T15:00:00+08:00",
        "ended_at": "2026-04-07T15:12:30+08:00",
        "duration_ms": 750000
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

## 9. 运行状态说明

### `running`

测试正在执行中。

### `completed`

所有启用的流程和循环都已执行完成。

### `failed`

运行因步骤失败或内部异常提前结束。

需要重点查看报告中的：

- `termination_reason` → `step_failed` 或 `internal_error`
- `termination_detail` → 具体错误信息
- 失败步骤的 `error_message`、`action`、`params`

### `paused`

运行因人工暂停而结束。

- 这不是失败，是正常的人工干预
- 已执行的部分会正常出报告
- 剩余未执行的流程/步骤不会继续

### `pausing`

暂停请求已发出，等待当前步骤执行完毕。这是一个过渡状态，很快会变为 `paused`。

## 10. 常见问题处理

### 问题 1：启动时报配置错误 `CONFIG_INVALID`

检查项：

- 配置文件路径是否正确（必须是 Linux 主机上的绝对路径）
- 文件是否存在
- YAML 格式是否正确（缩进、冒号后有空格）
- `version` 是否为 `1`
- `flows` 是否至少有一个
- `steps` 是否至少有一个
- `robot.move_to_pose` 是否提供了 `target_pose`
- `cup.dispense` / `cup.check` / `lid.pre_check` / `lid.dispense` 是否提供了 `cup_type`
- `cup_type` 是否为 `cold` / `hot` / `icecream`
- `lid.pre_check` 和 `lid.dispense` 不支持 `cup_type: icecream`
- `robot.check_gripper` 的 `expected` 是否为 `empty` 或 `holding`
- `flow.id` 是否有重复

### 问题 2：启动时报已有任务运行中 `RUN_ALREADY_ACTIVE`

同一时刻系统只允许一个任务运行。

处理方式：

1. 调用 `GET /api/v1/runs/current` 查看当前运行状态
2. 等当前任务自然结束
3. 或调用 `POST /api/v1/runs/pause` 暂停当前任务，等状态变为 `paused` 后再启动新任务

### 问题 3：查不到报告 `REPORT_NOT_FOUND`

检查项：

1. 任务是否真的已经结束（调用 `/api/v1/runs/current` 确认）
2. `run_id` 是否拼写正确
3. 是否查错了服务地址

### 问题 4：报告显示成功，但现场设备没有动作

检查 `/health` 返回中的 `simulate_bar_middleware_success`：

- 如果为 `true`，说明当前处于模拟模式，所有硬件动作直接返回成功，不会真正控制设备
- 真实测试时必须为 `false`

如果确认不是模拟模式，检查 `bar_middleware` 是否正常运行：

```bash
docker ps | grep barMiddleware
```

### 问题 5：步骤执行超时

可能原因：

- `bar_middleware` 未启动或异常
- 硬件设备故障（杯机卡杯、盖机卡盖等）
- 配置的 `timeout_ms` 过短

处理方式：

1. 检查 `bar_middleware` 容器状态
2. 检查现场硬件设备状态
3. 适当增大配置文件中的 `timeout_ms` 或 `runtime.default_timeout_ms`

### 问题 6：服务无法访问

如果 `http://192.168.42.1:18080/health` 无法打开：

1. 确认网络连通性（能否 ping 通 192.168.42.1）
2. SSH 登录主机检查服务状态：

```bash
sudo systemctl status hardware-module-test-service
```

3. 如果服务未运行，启动它：

```bash
sudo systemctl restart hardware-module-test-service
```

4. 查看服务日志排查原因：

```bash
sudo journalctl -u hardware-module-test-service -n 50 --no-pager
```

### 问题 7：主机重启后服务没有自动启动

两个服务都已配置为开机自启。如果没有自动启动：

```bash
# 检查状态
sudo systemctl status bar-middleware
sudo systemctl status hardware-module-test-service

# 手动启动
sudo systemctl restart bar-middleware
sudo systemctl restart hardware-module-test-service

# 查看日志
sudo journalctl -u bar-middleware -n 30 --no-pager
sudo journalctl -u hardware-module-test-service -n 30 --no-pager
```

`bar-middleware` 启动依赖 fluentd 容器的 24224 端口就绪，开机时会自动等待最多 120 秒。如果 fluentd 长时间未就绪，`bar-middleware` 可能启动失败，此时手动重启即可。

## 11. 配置文件修改说明

配置文件是每次调用 `/api/v1/runs/start` 时实时读取的，不是服务启动时加载的。

- 修改配置文件后不需要重启服务
- 新增配置文件后不需要重启服务
- 同一个文件路径，改了内容，下次启动测试读到的就是最新内容
- 只有修改了 Python 代码才需要重启服务

## 12. 建议操作规范

1. 每次启动测试前确认配置文件内容和 `/health` 状态
2. `operator` 字段填写真实操作人姓名或工号
3. 保存好返回的 `run_id`
4. 测试结束后下载并归档 HTML 报告和 JSON 报告
5. 如发生失败，优先记录：
   - `run_id`
   - 失败步骤名称和动作
   - 失败时间
   - 错误信息
   - 现场设备状态
6. 不要在测试运行中直接关闭主机或重启服务，应先暂停测试

## 13. 快速参考

日常最简操作流程：

```text
1. 浏览器打开 http://192.168.42.1:18080/docs
2. 调 GET /health → 确认 simulate_bar_middleware_success = false
3. 调 POST /api/v1/runs/start → 传入配置文件路径 → 记录 run_id
4. 调 GET /api/v1/runs/{run_id}/progress → 查看进度
5. 等待运行结束
6. 调 GET /api/v1/reports/{run_id} → 查看结果
7. 浏览器打开 /api/v1/reports/{run_id}/download/html → 下载 HTML 报告
```
