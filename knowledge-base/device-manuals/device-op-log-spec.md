# 设备操作日志规范速查

> 本文档是《无人值守饮品设备 — 设备端日志统一规范 v1》的速查版本，供开发人员在新增/修改日志时参考。

## 一、日志字段

### 必填字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `timestamp` | string | UTC+8，精确到毫秒 | `2026-03-05T14:35:12.123+08:00` |
| `level` | string | 日志级别 | `INFO` |
| `module` | string | 模块标识 | `CoffeeMachine` |
| `module_id` | string | 模块实例 ID | `CM_01` |
| `device_id` | string | 设备 SN | `C028` |
| `trace_id` | string | 链路追踪 ID | `ORD-C028-1741397130123` |
| `order_id` | string | 订单号（无订单时为 `""` ） | `ORD-202603051430002` |
| `event_type` | string | 事件类型 | `operation` |
| `message` | string | 人类可读描述 | `取杯成功，槽位 A3` |
| `source` | string | 来源项目 | `bar_middleware` |
| `log_type` | string | 固定值，用于 Fluentd 过滤 | `device_op` |

### 扩展字段（按需）

| 字段 | 类型 | 说明 |
|------|------|------|
| `error_code` | string | 统一错误码（仅 WARN/ERROR/FATAL） |
| `duration_ms` | number | 操作耗时（毫秒） |
| `details` | object | 结构化扩展数据 |

## 二、枚举定义

### level — 日志级别

| 值 | 语义 | 使用场景 |
|----|------|----------|
| `DEBUG` | 调试 | 开发/临时诊断，默认不采集 |
| `INFO` | 信息 | 正常业务流转 |
| `WARN` | 警告 | 可恢复异常、物料低库存 |
| `ERROR` | 错误 | 不可恢复异常、操作失败 |
| `FATAL` | 致命 | 整机停机、进程崩溃 |

### event_type — 事件类型

| 值 | 语义 | 典型场景 |
|----|------|----------|
| `operation` | 设备运行 | 机械臂动作、咖啡机制作、落杯、扣盖 |
| `material` | 物料报警 | 杯量低、糖浆不足、冰量不足 |
| `api` | 接口请求 | HTTP/WebSocket 请求响应 |
| `system` | 系统运行 | CPU/内存/磁盘、心跳、固件版本 |
| `deploy` | 部署运维 | 容器启停、固件升级、配置变更 |

### source — 来源项目

| 值 | 项目 |
|----|------|
| `bar_middleware` | bar_middleware |
| `deploy_client` | bar-deploy-client |
| `order_agent` | orderStatusAgent |
| `quokka` | Quokka251 |
| `tools` | tools |

### module — 模块枚举

| module | module_id 前缀 | 说明 |
|--------|---------------|------|
| `RoboticArm` | RA | 机械臂 |
| `CoffeeMachine` | CM | 咖啡机 |
| `CupDispenser` | CD | 落杯器 |
| `LidMachine` | LM | 扣盖机 |
| `Pump` | PP | 蠕动泵 |
| `SyrupDispenser` | SD | 糖浆机 |
| `IceMachine` | IM | 制冰机 |
| `IceCreamMachine` | IC | 冰淇淋机 |
| `PowderDispenser` | PD | 粉料机 |
| `BeverageDispenser` | BD | 饮料机 |
| `Delivery` | DL | 出餐口/传送 |
| `Scanner` | SC | 扫码器 |
| `Printer` | PR | 打印机/标签机 |
| `ELock` | EL | 电子锁 |
| `Lights` | LT | 灯光/DMX |
| `PowerCtrl` | PC | 电源控制 |
| `SnowMelter` | SM | 融雪机 |
| `Position` | PS | 位置检测 |
| `Screen` | SN | 屏幕 |
| `IOBoard` | IO | IO 板 |
| `APIGateway` | AG | HTTP/API 网关 |
| `MessageQueue` | MQ | 消息队列 |
| `LogicLock` | LL | 逻辑锁 |
| `SystemMonitor` | SY | 系统监控 |
| `CupCapper` | CC | 杯盖机 |
| `Device` | DV | 整机/进程级 |
| `Agent` | AT | 制作调度 |
| `Firmware` | FW | 固件 |

## 三、trace_id 生成规则

| 场景 | 格式 | 示例 |
|------|------|------|
| 订单制作 | `ORD-{device_id}-{timestamp_ms}` | `ORD-C028-1741397130123` |
| 设备操作 | `DEV-{device_id}-{timestamp_ms}` | `DEV-C028-1741373601000` |
| 运维指令 | `MNT-{device_id}-{timestamp_ms}` | `MNT-C028-1741396920200` |
| 系统监控 | `SYS-{device_id}-{timestamp_ms}` | `SYS-C028-1741397100000` |
| 物料报警 | `MATL-{device_id}-{timestamp_ms}` | `MATL-C028-1741396800500` |

## 四、错误码规范

### 格式

```
{模块码}-{子类型码(3位)}-{异常码(4位)}
```

示例：`LM-002-0001` = 扣盖机-动作执行-超时

### 子类型码

| 码 | 含义 |
|----|------|
| 001 | 通信异常 |
| 002 | 动作执行 |
| 003 | 传感器故障 |
| 004 | 物料相关 |
| 005 | 定位问题 |
| 006 | 温控异常 |
| 007 | 硬件故障 |
| 008 | 软件逻辑 |

### 异常码

| 码 | 含义 |
|----|------|
| 0001 | 超时 |
| 0002 | 数值异常 |
| 0003 | 卡阻 |
| 0004 | 无响应 |
| 0005 | 低库存 |
| 0006 | 压力异常 |
| 0007 | 识别失败 |
| 0008 | 校准错误 |

### 扩展规则

- 新增模块：按 module 枚举表新增 2 位字母码
- 新增子类型：从 `009` 递增
- 新增异常码：从 `0009` 递增

## 五、错误码速查表

### 按 error_code 查找

| error_code | module | 含义 | 原始码 |
|------------|--------|------|--------|
| LM-002-0001 | LidMachine | 扣盖超时 | IoResult 102, 105 |
| LM-002-0004 | LidMachine | 扣盖指令无响应 | IoResult 101 |
| LM-003-0002 | LidMachine | 杯子超高 | IoResult 104 |
| LM-003-0007 | LidMachine | 未检测到杯盖/托盘异物/无杯 | IoResult 103, 201, 202, 203 |
| LM-005-0001 | LidMachine | 扣盖机未归位 | IoResult 100 |
| CD-002-0004 | CupDispenser | 落杯 Dump 失败 | IoResult 111 |
| CD-008-0002 | CupDispenser | Dump 状态未清除 | IoResult 112 |
| CM-001-xxxx | CoffeeMachine | 咖啡机通信异常 | Eversys E-095~E-099 |
| CM-006-xxxx | CoffeeMachine | 咖啡机温控/水路异常 | Eversys E-010~E-016 |
| CM-007-xxxx | CoffeeMachine | 咖啡机硬件故障 | Eversys E-000~E-005 |
| RA-001-0004 | RoboticArm | 机械臂连接失败 | 300s 重试未成功 |

### 按场景查找

| 场景 | 去哪里看 | 关键字段 |
|------|----------|----------|
| 饮品制作失败 | source=quokka, module=Agent | trace_id 以 ORD- 开头 |
| 落杯失败 | source=bar_middleware, module=CupDispenser | error_code 以 CD- 开头 |
| 扣盖失败 | source=quokka, module=LidMachine | error_code 以 LM- 开头 |
| 机械臂异常 | module=RoboticArm | error_code 以 RA- 开头 |
| 咖啡机异常 | module=CoffeeMachine | error_code 以 CM- 开头 |
| 云端指令失败 | source=deploy_client, event_type=api | message 含"指令执行失败" |
| 物料报警 | event_type=material | source=deploy_client |
| WebSocket 断连 | module=APIGateway, event_type=system | message 含"连接失败"或"重连" |
| 系统资源告警 | source=tools, module=SystemMonitor | level=WARN 或 ERROR |
| 开机/关机 | module=Device, event_type=operation | message 含"开机"或"关机" |
| 程序崩溃 | level=FATAL 或 module=Device | message 含"未捕获异常" |

### 常用排查命令

```bash
# 查看某个订单的完整链路
grep "ORD-C028-1741397130123" /home/smyze/logs/device_op/devices_op.log

# 查看所有错误
grep '"level":"ERROR"' /home/smyze/logs/device_op/devices_op.log | jq .

# 查看某个模块的错误
grep '"module":"LidMachine"' /home/smyze/logs/device_op/devices_op.log | grep '"level":"ERROR"'

# 查看物料报警
grep '"event_type":"material"' /home/smyze/logs/device_op/devices_op.log

# 查看最近 10 条错误
grep '"level":"ERROR"' /home/smyze/logs/device_op/devices_op.log | tail -10 | jq .

# 按时间范围查看
grep '"level":"ERROR"' /home/smyze/logs/device_op/devices_op.log | grep '2026-03-12T14' | jq .
```
