# bar-deploy-client 设备操作日志改造说明

## 概述

本次改造为 bar-deploy-client 新增了统一设备操作日志输出，通过 Logback Console Appender 输出 JSON 到 stdout，由 Fluentd 收集后写入统一日志文件。原有 FILE 和 SYS_ERROR Appender 完全保留不变。

## 改造内容

### 新增文件

| 文件 | 说明 |
|------|------|
| `common/aop/DeviceOpLog.java` | 注解定义，标注在方法上自动记录 |
| `common/aop/DeviceOpLogAspect.java` | AOP 切面，拦截 @DeviceOpLog 注解 |
| `common/config/thread/MdcTaskDecorator.java` | MDC 上下文线程传递 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `pom.xml` | 添加 logstash-logback-encoder 8.0 |
| `logback-spring.xml` | 新增 DEVICE_OP_CONSOLE appender + device.op logger |
| `timer/co2/AsyncConfig.java` | 注册 MdcTaskDecorator |
| `common/config/SchedulingConfig.java` | 定时任务异常捕获 |
| `service/webscoket/DeviceOpsWebSocketMessageListener.java` | MDC 注入 + 指令日志 |
| `service/webscoket/WebSocketClientServiceImpl.java` | 连接/重连/发送失败日志 |
| `cloud/CloudApi.java` | 云端上报失败日志 |
| `service/webscoket/handler/DeviceMaterialAlertHandler.java` | 物料报警日志 |
| `service/webscoket/handler/DeviceStatusAlertHandler.java` | 设备告警日志 |
| `service/webscoket/handler/DevicEnvironmentAlertHandler.java` | 环境报警日志 |

## 工作流程

```
业务代码使用 deviceOpLog logger 或 @DeviceOpLog 注解
    ↓
Logback DEVICE_OP_CONSOLE appender 输出 JSON 到 stdout
    ↓
Docker --log-driver=fluentd 转发到 Fluentd
    ↓
Fluentd grep 过滤 "log_type":"device_op"
    ↓
写入 /home/smyze/logs/device_op/devices_op.log
```

## 关键机制

### 1. 专用 Logger

设备操作日志使用独立的 logger name `device.op`，只有这个 logger 输出到 DEVICE_OP_CONSOLE，不影响原有日志：

```java
private static final Logger deviceOpLog = LoggerFactory.getLogger("device.op");
```

### 2. MDC 上下文注入

在 WebSocket 消息入口自动注入 MDC：

```java
MDC.put("trace_id", "MNT-" + DEVICE_ID + "-" + System.currentTimeMillis());
MDC.put("device_id", DEVICE_ID);
MDC.put("module", dto.getTarget());
MDC.put("event_type", "api");
try {
    // 业务逻辑，所有 deviceOpLog 调用自动携带上下文
} finally {
    MDC.clear();
}
```

### 3. MdcTaskDecorator

解决 @Async 线程池中 MDC 上下文丢失问题，已注册到 AsyncConfig。

### 4. 定时任务异常捕获

SchedulingConfig 中设置了 ErrorHandler，所有 @Scheduled 方法的异常自动记录到设备操作日志。

## 如何新增埋点

### 方式 1：使用 @DeviceOpLog 注解（推荐）

```java
@DeviceOpLog(module = "CoffeeMachine", eventType = "api")
public void myMethod() {
    // 自动记录执行时间、成功/失败
}
```

### 方式 2：手动使用 deviceOpLog

```java
private static final Logger deviceOpLog = LoggerFactory.getLogger("device.op");

// 记录前先设置 MDC
MDC.put("module", "CoffeeMachine");
MDC.put("event_type", "api");
try {
    deviceOpLog.atInfo().log("操作开始");
    // ... 业务逻辑 ...
    deviceOpLog.atInfo()
        .addKeyValue("duration_ms", duration)
        .log("操作完成");
} finally {
    MDC.clear();
}
```

### 方式 3：在 Handler 中添加

参考 DeviceMaterialAlertHandler 的实现：

```java
private static final Logger deviceOpLog = LoggerFactory.getLogger("device.op");

deviceOpLog.atWarn()
    .addKeyValue("module", "ModuleName")
    .addKeyValue("event_type", "material")
    .log("报警信息: {} {}", name, message);
```

## 注意事项

- 只使用 `LoggerFactory.getLogger("device.op")` 输出设备操作日志
- 使用 MDC 传递上下文（trace_id/device_id/module/event_type）
- 方法结束后必须 `MDC.clear()` 或使用 try-finally
- @DeviceOpLog 注解需要 Spring AOP 支持（方法必须通过 Spring 代理调用）
- logback-spring.xml 中 `customFields` 已自动添加 `log_type` 和 `source` 字段
