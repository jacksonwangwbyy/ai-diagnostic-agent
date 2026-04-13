# 网络与部署故障案例

## 案例 1：OTA 升级失败（下载中断）

### 故障现象
设备在执行 OTA 升级时，下载进度停滞后报错终止。升级包未完整下载，设备仍运行旧版本固件，控制台显示升级失败。

### 涉及模块
bar-deploy-client（OTA 升级客户端）

### 关键日志
```
2026-04-10 02:15:03 INFO  [bar-deploy-client] Starting OTA download: version=2.1.0, size=256MB
2026-04-10 02:15:03 DEBUG [bar-deploy-client] Downloading from https://ota.smyze.com/releases/2.1.0/update.tar.gz
2026-04-10 02:28:41 ERROR [bar-deploy-client] Download interrupted: ConnectionResetError after 87MB/256MB
2026-04-10 02:28:41 ERROR [bar-deploy-client] OTA failed: incomplete package, aborting installation
2026-04-10 02:28:42 WARN  [bar-deploy-client] Rollback not needed: old version still active
```

### 故障原因
网络连接不稳定导致下载中途断开，升级包未完整下载，部署客户端拒绝安装不完整的升级包。

### 解决方案
1. 检查网络连通性：`ping ota.smyze.com` 及 `curl -I https://ota.smyze.com`
2. 清除不完整的下载缓存：`rm -rf /home/smyze/bar_middleware/ota/tmp/`
3. 在网络稳定时段重新触发升级：`bar-deploy-client upgrade --version 2.1.0`
4. 若网络持续不稳定，使用断点续传选项：`bar-deploy-client upgrade --version 2.1.0 --resume`
5. 升级完成后验证版本：`bar-deploy-client status`

### 预防措施
- OTA 客户端实现断点续传，避免因短暂断网导致重新下载
- 升级前检查网络质量，信号弱时推迟升级任务
- 下载完成后校验 MD5/SHA256，确保包完整性再执行安装

---

## 案例 2：版本同步不一致

### 故障现象
多台设备执行批量升级后，部分设备版本未更新成功，导致同一批次设备运行不同版本。版本不一致引发跨设备协同功能异常。

### 涉及模块
bar-deploy-client（版本管理与同步）

### 关键日志
```
2026-04-11 03:00:15 INFO  [bar-deploy-client] Batch upgrade initiated: 8 devices, target=2.1.0
2026-04-11 03:00:15 DEBUG [bar-deploy-client] Device 192.168.42.3 upgrade: SUCCESS, version=2.1.0
2026-04-11 03:00:15 ERROR [bar-deploy-client] Device 192.168.42.5 upgrade: FAILED, version=2.0.3 (unchanged)
2026-04-11 03:00:16 WARN  [bar-deploy-client] Version mismatch detected across fleet: 2.1.0 x6, 2.0.3 x2
2026-04-11 03:00:16 ERROR [bar-deploy-client] Fleet consistency check FAILED
```

### 故障原因
批量升级时部分设备网络超时或磁盘空间不足，导致升级失败，但批量任务未对失败设备进行重试。

### 解决方案
1. 查询各设备当前版本：`bar-deploy-client fleet-status`
2. 对失败设备单独重新升级：`bar-deploy-client upgrade --target 192.168.42.5 --version 2.1.0`
3. 检查失败设备磁盘空间：`ssh smyze@192.168.42.5 "df -h"`
4. 若磁盘不足，清理旧版本备份：`ssh smyze@192.168.42.5 "bar-deploy-client cleanup --keep 1"`
5. 升级完成后再次验证全部设备版本一致

### 预防措施
- 批量升级任务对失败设备自动重试 3 次
- 升级前检查所有目标设备的磁盘空间和网络状态
- 升级完成后自动执行版本一致性校验，不一致时告警

---

## 案例 3：SSH 远程连接超时

### 故障现象
运维人员尝试通过 SSH 连接设备 192.168.42.1 进行远程维护，连接请求长时间无响应后超时断开。设备本地功能正常，但无法远程访问。

### 涉及模块
SSH 服务（设备远程管理，192.168.42.1:22）

### 关键日志
```
2026-04-11 10:30:05 INFO  [sshd] Connection attempt from 192.168.1.100 to 192.168.42.1:22
2026-04-11 10:30:05 WARN  [sshd] Max connections reached: 10/10 active sessions
2026-04-11 10:30:05 ERROR [sshd] Connection rejected: too many open connections
2026-04-11 10:30:05 WARN  [syslog] sshd: refused connect from 192.168.1.100 (192.168.1.100)
```

### 故障原因
SSH 并发连接数达到上限，通常由僵尸 SSH 会话未正常关闭积累导致，新连接请求被拒绝。

### 解决方案
1. 从设备本地终端查看当前 SSH 会话：`who` 或 `ss -tnp | grep :22`
2. 终止僵尸会话：`sudo pkill -u smyze sshd` 或指定 PID kill
3. 临时增加最大连接数：编辑 `/etc/ssh/sshd_config`，将 `MaxSessions` 调整为 20
4. 重启 SSH 服务：`sudo systemctl restart sshd`
5. 重新尝试连接：`ssh smyze@192.168.42.1`

### 预防措施
- 配置 SSH 会话超时自动断开：在 `sshd_config` 中设置 `ClientAliveInterval 300` 和 `ClientAliveCountMax 2`
- 运维操作完成后养成主动退出 SSH 会话的习惯
- 监控 SSH 活跃连接数，接近上限时告警

---

## 案例 4：Docker 容器重启循环（CrashLoopBackOff）

### 故障现象
bar_middleware Docker 容器持续重启，每次启动后数秒内即退出。`docker ps` 显示容器状态为 Restarting，服务完全不可用。

### 涉及模块
Docker 容器（bar_middleware 服务容器）

### 关键日志
```
2026-04-12 05:10:01 ERROR [docker] Container bar_middleware exited with code 1
2026-04-12 05:10:01 INFO  [docker] Restarting container bar_middleware (attempt 5)
2026-04-12 05:10:03 ERROR [bar_middleware] Failed to connect to database: Connection refused at localhost:5432
2026-04-12 05:10:03 ERROR [bar_middleware] Startup check failed: required service unavailable
2026-04-12 05:10:03 ERROR [docker] Container bar_middleware exited with code 1 after 2s
```

### 故障原因
容器启动时依赖的数据库或其他服务尚未就绪，中间件启动检查失败后退出，触发 Docker 重启策略形成循环。

### 解决方案
1. 查看容器退出日志：`docker logs bar_middleware --tail 50`
2. 检查依赖服务状态：`docker ps -a | grep postgres`
3. 先启动依赖服务：`docker start postgres_container`
4. 等待依赖服务就绪后再启动中间件：`docker start bar_middleware`
5. 长期方案：在 `docker-compose.yml` 中为 bar_middleware 添加 `depends_on` 和健康检查等待

### 预防措施
- 使用 `docker-compose` 管理服务依赖顺序，配置 `depends_on` 和 `condition: service_healthy`
- 中间件启动时对依赖服务实现重试等待逻辑，而非立即失败退出
- 配置容器重启策略为 `on-failure:5`，避免无限重启消耗资源

---

## 案例 5：视频内容下发失败

### 故障现象
设备屏幕未按计划更新广告或菜单视频内容，仍显示旧版内容。后台下发任务显示已发送，但设备端未收到或未成功应用新内容。

### 涉及模块
bar-deploy-client（内容分发模块）

### 关键日志
```
2026-04-12 08:00:03 INFO  [bar-deploy-client] Content push task started: video_menu_v3.mp4 -> 192.168.42.1
2026-04-12 08:00:03 DEBUG [bar-deploy-client] Transferring file via SCP: 128MB
2026-04-12 08:05:11 ERROR [bar-deploy-client] SCP transfer failed: No space left on device (192.168.42.1)
2026-04-12 08:05:11 ERROR [bar-deploy-client] Content deployment failed for device 192.168.42.1
2026-04-12 08:05:12 WARN  [bar-deploy-client] Device 192.168.42.1 content version: v2 (expected: v3)
```

### 故障原因
目标设备存储空间不足，无法接收新的视频文件，SCP 传输失败导致内容未更新。

### 解决方案
1. 检查设备存储空间：`ssh smyze@192.168.42.1 "df -h /home/smyze/media/"`
2. 清理旧版本视频文件：`ssh smyze@192.168.42.1 "rm /home/smyze/media/video_menu_v1.mp4 /home/smyze/media/video_menu_v2.mp4"`
3. 确认空间释放后重新下发内容：`bar-deploy-client push-content --target 192.168.42.1 --file video_menu_v3.mp4`
4. 验证内容已更新：`ssh smyze@192.168.42.1 "ls -lh /home/smyze/media/"`
5. 重启媒体播放服务使新内容生效：`ssh smyze@192.168.42.1 "sudo systemctl restart media_player"`

### 预防措施
- 下发新内容前自动检查目标设备可用存储空间
- 内容下发成功后自动删除旧版本文件，保持存储空间充裕
- 配置设备存储使用率监控，超过 85% 时提前告警
