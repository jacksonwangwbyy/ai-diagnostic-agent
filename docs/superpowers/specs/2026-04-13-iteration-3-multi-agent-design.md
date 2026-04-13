# 迭代 3：多 Agent 协作系统 设计方案

> 日期: 2026-04-13
> 状态: 已确认
> 前置: 迭代 1（质量保障）+ 迭代 2（RAG 优化 + 新工具）已完成

## 概述

从单 Agent 升级为 Supervisor 编排的多 Agent 协作系统。Supervisor 接收用户请求，根据意图路由到专业 Agent，汇总结果返回。

> **实现说明（2026-04-13）：**
> - Supervisor 使用函数路由而非 LangGraph StateGraph，功能等价且更简洁
> - 多 Agent 响应字段扩展到现有 `DiagnoseResponse`（新增 `route`、`agents_used`），而非新增 `MultiAgentResponse`

## 架构

```
用户请求 → Supervisor Agent（意图识别 + 路由）
                ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
 诊断 Agent  维修 Agent  监控 Agent
 (6个工具)   (知识库+报告) (状态+日志)
    └───────────┼───────────┘
                ↓
        Supervisor 汇总 → 最终响应
```

### Supervisor Agent

- 基于 LangGraph StateGraph 构建
- 职责：接收用户请求 → 分析意图 → 路由到对应 Agent → 汇总结果
- 路由策略：
  - 故障诊断类 → 诊断 Agent（现有）
  - 维修方案类 → 维修 Agent
  - 状态监控类 → 监控 Agent
  - 复杂问题 → 诊断 Agent → 维修 Agent（链式调用）

### 诊断 Agent（现有，保持不变）

- 6 个工具：知识库搜索、日志读取、设备状态、诊断报告、服务重启、固件检查
- ReAct 模式，自主决策工具调用

### 维修建议 Agent（新增）

- 工具：知识库搜索、诊断报告生成
- 专注于：根据诊断结果生成维修方案、备件清单、操作步骤
- 输入：诊断结论（来自诊断 Agent 或用户直接描述）

### 设备监控 Agent（新增）

- 工具：设备状态查询、日志读取、固件版本检查
- 专注于：设备健康检查、异常检测、状态汇总
- 输入：监控请求（如"检查所有设备状态"）

## 新增文件

| 文件 | 职责 |
|------|------|
| `src/agent/supervisor.py` | Supervisor 编排引擎 |
| `src/agent/repair_agent.py` | 维修建议 Agent |
| `src/agent/monitor_agent.py` | 设备监控 Agent |
| `src/api/models.py` | 新增 MultiAgentResponse |
| `tests/test_supervisor.py` | Supervisor 测试 |
| `tests/test_repair_agent.py` | 维修 Agent 测试 |
| `tests/test_monitor_agent.py` | 监控 Agent 测试 |

## 修改文件

| 文件 | 变更 |
|------|------|
| `src/api/routes.py` | `/diagnose` 端点使用 Supervisor |
| `README.md` | 更新架构说明、Agent 列表 |
| `docs/usage-and-learning-guide.md` | 添加多 Agent 章节 |

## 向后兼容

- 现有 `/api/diagnose` 端点行为不变（Supervisor 默认路由到诊断 Agent）
- `create_diagnostic_agent()` 函数保留，可独立使用
- `run_diagnosis()` 函数保留
