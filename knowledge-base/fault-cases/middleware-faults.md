# 中间件（bar_middleware）故障案例

## 案例 1：中间件服务启动失败（端口占用）

### 故障现象
操作员发现 bar_middleware 服务无法启动，设备管理后台显示中间件离线。尝试重启服务后仍报错，所有依赖中间件的接口均不可用。

### 涉及模块
bar_middleware（FastAPI Python 服务，监听端口 8003）

### 关键日志
```
2026-04-10 08:12:03 ERROR [bar_middleware] Failed to bind to port 8003: Address already in use
2026-04-10 08:12:03 ERROR [uvicorn] OSError: [Errno 98] Address already in use
2026-04-10 08:12:04 ERROR [bar_middleware] Service startup failed, exiting with code 1
2026-04-10 08:12:04 WARN  [supervisor] bar_middleware exited unexpectedly, restart attempt 1/3
```

### 故障原因
上一次服务异常退出时未正确释放端口 8003，导致残留进程占用该端口，新实例无法绑定启动。

### 解决方案
1. 查找占用端口的进程：`ss -tlnp | grep 8003`
2. 终止占用进程：`kill -9 <PID>`
3. 确认端口已释放：`ss -tlnp | grep 8003`（应无输出）
4. 重启服务：`sudo systemctl restart bar_middleware`
5. 验证服务状态：`curl http://localhost:8003/health`

### 预防措施
- 配置 supervisor 或 systemd 的 `ExecStopPost` 钩子，在服务停止时自动清理端口
- 设置服务启动前检查脚本，检测端口占用并自动处理
- 启用 `SO_REUSEPORT` 套接字选项减少端口冲突概率

---

## 案例 2：中间件接口响应超时

### 故障现象
前端设备控制界面操作无响应，HTTP 请求长时间挂起后返回 504 超时错误。日志显示中间件接收到请求但未能在规定时间内返回响应。

### 涉及模块
bar_middleware（FastAPI 异步接口层，依赖下游硬件模块 HTTP 调用）

### 关键日志
```
2026-04-10 14:23:11 INFO  [bar_middleware] Received POST /robot/action from 192.168.42.10
2026-04-10 14:23:11 DEBUG [bar_middleware] Forwarding request to robot arm service at 192.168.42.1:8001
2026-04-10 14:23:41 ERROR [bar_middleware] Upstream timeout after 30s: robot arm service did not respond
2026-04-10 14:23:41 ERROR [bar_middleware] Request /robot/action failed with HTTPTimeoutError
2026-04-10 14:23:41 WARN  [bar_middleware] Returning 504 Gateway Timeout to client
```

### 故障原因
下游机械臂服务响应缓慢或无响应，中间件等待超时，导致请求积压，最终触发级联超时。

### 解决方案
1. 检查下游服务状态：`curl -m 5 http://192.168.42.1:8001/RobotArm/Dev/status`
2. 查看中间件当前连接数：`ss -s` 及 `cat /home/smyze/bar_middleware/logs/app.log | tail -100`
3. 重启下游服务（如机械臂服务）：`sudo systemctl restart robot_arm_service`
4. 调整中间件超时配置：编辑 `/home/smyze/bar_middleware/config.yaml`，将 `upstream_timeout` 适当增大
5. 重启中间件：`sudo systemctl restart bar_middleware`

### 预防措施
- 为所有下游调用配置合理的超时时间（建议 10s），避免无限等待
- 实现熔断器模式，下游连续失败时快速返回错误
- 配置 Prometheus 监控接口响应时间，超阈值自动告警

---

## 案例 3：中间件与硬件模块通信断开

### 故障现象
设备状态面板显示多个硬件模块离线，中间件日志持续报告无法连接硬件控制服务。重启中间件后问题依旧，但硬件模块本身指示灯正常。

### 涉及模块
bar_middleware（与硬件模块通过内网 192.168.42.x 通信）

### 关键日志
```
2026-04-11 09:05:17 ERROR [bar_middleware] Cannot connect to ice machine at 192.168.42.1:8010: Connection refused
2026-04-11 09:05:17 ERROR [bar_middleware] Cannot connect to coffee machine at 192.168.42.1:8011: Connection refused
2026-04-11 09:05:18 WARN  [bar_middleware] Hardware module health check failed: 3/5 modules unreachable
2026-04-11 09:05:20 ERROR [bar_middleware] NetworkError: Failed to reach 192.168.42.1 - No route to host
```

### 故障原因
内网网络配置变更或网络接口重启导致 192.168.42.x 网段路由丢失，中间件无法访问硬件模块。

### 解决方案
1. 检查网络连通性：`ping 192.168.42.1`
2. 查看路由表：`ip route show`
3. 检查网络接口状态：`ip addr show`
4. 若路由丢失，手动添加：`sudo ip route add 192.168.42.0/24 dev eth0`
5. 持久化路由配置：编辑 `/etc/netplan/` 或 `/etc/network/interfaces`，确保重启后路由保留

### 预防措施
- 将内网路由配置写入系统网络配置文件，防止重启后丢失
- 配置中间件启动时自动检测网络连通性，不满足条件时延迟启动
- 部署网络监控，192.168.42.1 不可达时立即告警

---

## 案例 4：中间件内存泄漏导致 OOM

### 故障现象
中间件运行数小时后响应逐渐变慢，最终被系统 OOM Killer 强制终止。服务自动重启后恢复正常，但周期性出现。

### 涉及模块
bar_middleware（Python FastAPI 进程，运行于 Docker 容器或直接部署）

### 关键日志
```
2026-04-11 22:41:03 WARN  [bar_middleware] Memory usage at 85%: 1740MB / 2048MB
2026-04-11 22:41:45 WARN  [bar_middleware] Memory usage at 95%: 1946MB / 2048MB
2026-04-11 22:42:01 ERROR [kernel] Out of memory: Kill process 3821 (python3) score 892 or sacrifice child
2026-04-11 22:42:01 ERROR [kernel] Killed process 3821 (python3) total-vm:2150MB, anon-rss:1998MB
2026-04-11 22:42:02 WARN  [supervisor] bar_middleware killed by signal 9, restarting
```

### 故障原因
中间件代码中存在未释放的对象引用（如缓存未设上限、异步任务未清理），导致内存持续增长直至 OOM。

### 解决方案
1. 查看内存增长趋势：`cat /home/smyze/bar_middleware/logs/app.log | grep -i memory`
2. 使用 `tracemalloc` 或 `memory_profiler` 对中间件进行内存分析，定位泄漏点
3. 检查代码中的全局缓存、连接池是否设置了最大容量限制
4. 临时缓解：在 systemd 服务配置中添加 `MemoryMax=1G` 限制内存上限并触发重启
5. 修复泄漏代码后重新部署：`sudo systemctl restart bar_middleware`

### 预防措施
- 为 Docker 容器或 systemd 服务配置内存上限，防止影响其他进程
- 定期（每日）轮转重启中间件服务作为临时缓解手段
- 集成内存监控指标，内存超过 80% 时自动告警并触发分析

---

## 案例 5：中间件日志写入失败

### 故障现象
运维人员发现 `/home/smyze/bar_middleware/logs/app.log` 长时间未更新，无法通过日志排查问题。中间件服务本身仍在运行，但所有日志输出静默丢失。

### 涉及模块
bar_middleware（Python logging 模块，日志路径 /home/smyze/bar_middleware/logs/）

### 关键日志
```
2026-04-12 06:00:01 ERROR [python.logging] Failed to open log file: [Errno 28] No space left on device
2026-04-12 06:00:01 ERROR [python.logging] Logging handler error, disabling file handler
2026-04-12 06:00:05 WARN  [bar_middleware] Log file handler disabled due to write error
```

### 故障原因
磁盘空间耗尽（通常由旧日志文件堆积或其他服务写满磁盘），导致日志文件无法写入，Python logging 自动禁用文件处理器。

### 解决方案
1. 检查磁盘使用情况：`df -h /home/smyze/bar_middleware/logs/`
2. 查找大文件：`du -sh /home/smyze/bar_middleware/logs/*`
3. 清理旧日志：`find /home/smyze/bar_middleware/logs/ -name "*.log.*" -mtime +7 -delete`
4. 重启中间件以重新初始化日志处理器：`sudo systemctl restart bar_middleware`
5. 验证日志恢复写入：`tail -f /home/smyze/bar_middleware/logs/app.log`

### 预防措施
- 配置 logrotate 定期轮转并压缩日志文件，保留最近 7 天
- 设置磁盘使用率告警，超过 80% 时通知运维
- 在中间件配置中设置日志文件最大大小和备份数量限制

---

## 案例 6：中间件版本不匹配

### 故障现象
OTA 升级后，中间件启动成功但部分接口返回 422 或 500 错误。前端设备控制功能异常，日志显示接口参数解析失败。

### 涉及模块
bar_middleware（FastAPI 服务）与前端控制客户端版本不兼容

### 关键日志
```
2026-04-12 10:15:22 ERROR [bar_middleware] Validation error on POST /robot/action: field 'grip_force' not found in schema v2.1
2026-04-12 10:15:22 INFO  [bar_middleware] Current API schema version: 2.1, client sent schema version: 2.0
2026-04-12 10:15:23 ERROR [bar_middleware] Unprocessable Entity: 1 validation error for RobotActionRequest
2026-04-12 10:15:23 WARN  [bar_middleware] Version mismatch detected: middleware=2.1.0, deploy-client=2.0.3
```

### 故障原因
OTA 升级仅更新了中间件服务，未同步更新前端控制客户端，导致 API 请求体结构不匹配。

### 解决方案
1. 确认各组件版本：`curl http://localhost:8003/version` 及 `bar-deploy-client --version`
2. 查看版本兼容性矩阵：`cat /home/smyze/bar_middleware/CHANGELOG.md`
3. 同步升级前端控制客户端至匹配版本：`sudo bar-deploy-client update --version 2.1.x`
4. 若无法立即升级客户端，可回滚中间件：`sudo bar-deploy-client rollback bar_middleware`
5. 升级完成后验证接口：`curl -X POST http://localhost:8003/robot/action -d '{"grip_force": 50}'`

### 预防措施
- OTA 升级流程中强制检查所有组件版本兼容性，不兼容时阻止升级
- 中间件 API 变更时保持向后兼容，至少支持上一个主版本的请求格式
- 升级前在测试环境验证全链路功能正常
