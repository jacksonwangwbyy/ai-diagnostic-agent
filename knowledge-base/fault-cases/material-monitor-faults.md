# 物料监控故障案例

## 案例 1：物料余量误报（传感器漂移）

### 故障现象
物料监控界面显示某通道余量为负值或异常高值，与实际库存明显不符。操作员补充物料后数值仍不正确，系统频繁触发虚假的低库存告警。

### 涉及模块
物料监控服务（/agent/material/all API，传感器数据采集模块）

### 关键日志
```
2026-04-10 10:05:22 WARN  [material_monitor] Channel 3 weight sensor reading: -0.23kg, expected range: 0-5kg
2026-04-10 10:05:22 ERROR [material_monitor] Abnormal reading on channel 3: value out of valid range
2026-04-10 10:05:23 WARN  [bar_middleware] GET /agent/material/all: channel_3 quantity=-0.23, triggering low stock alert
2026-04-10 10:05:25 ERROR [material_monitor] Sensor drift detected: zero-point offset exceeds 0.1kg threshold
```

### 故障原因
重量传感器长期使用后发生零点漂移，基准值偏移导致读数持续偏低或出现负值。

### 解决方案
1. 查询当前传感器读数：`curl http://localhost:8003/agent/material/all`
2. 清空对应通道物料，对传感器执行清零校准：`curl -X POST http://localhost:8003/agent/material/channel/3/calibrate`
3. 放回已知重量的物料验证校准结果
4. 若校准后仍漂移，检查传感器接线和固定螺丝是否松动
5. 更换传感器后重新校准并更新配置文件中的传感器参数

### 预防措施
- 每月定期对所有通道传感器执行一次零点校准
- 配置传感器读数合理性检查，超出物理范围时自动标记为异常而非直接告警
- 记录传感器历史读数趋势，漂移速率加快时提前预警

---

## 案例 2：通道传感器失灵

### 故障现象
某物料通道传感器完全无响应，API 返回该通道数据为 null 或固定不变。无论实际物料多少，读数始终为同一数值，导致库存管理失效。

### 涉及模块
物料监控服务（通道传感器硬件接口）

### 关键日志
```
2026-04-11 08:20:11 ERROR [material_monitor] Channel 5 sensor read failed: I2C communication error
2026-04-11 08:20:11 ERROR [material_monitor] Sensor at address 0x4A not responding
2026-04-11 08:20:12 WARN  [material_monitor] Channel 5 data marked as UNAVAILABLE
2026-04-11 08:20:12 WARN  [bar_middleware] /agent/material/all: channel_5 status=sensor_error, last_valid=2026-04-11T07:55:03
```

### 故障原因
传感器 I2C 通信故障，可能由接线松动、传感器损坏或 I2C 总线冲突引起。

### 解决方案
1. 检查传感器物理连接，重新插拔 I2C 接线
2. 扫描 I2C 总线确认设备是否可见：`i2cdetect -y 1`
3. 若设备不可见，检查供电电压是否正常（应为 3.3V 或 5V）
4. 更换备用传感器，更新配置文件中对应通道的传感器地址
5. 重启物料监控服务：`sudo systemctl restart material_monitor`

### 预防措施
- 备用关键通道传感器，发生故障时可快速更换
- 配置传感器失联告警，失联超过 5 分钟立即通知运维
- 定期检查 I2C 总线上所有设备的响应状态

---

## 案例 3：物料补充后数据未更新

### 故障现象
操作员完成物料补充操作后，监控界面的库存数量未发生变化，仍显示补充前的低库存状态。手动刷新页面后数据依然未更新。

### 涉及模块
物料监控服务（数据采集与缓存层）

### 关键日志
```
2026-04-11 14:30:05 INFO  [material_monitor] Replenishment event received for channel 2
2026-04-11 14:30:05 DEBUG [material_monitor] Triggering sensor re-read for channel 2
2026-04-11 14:30:06 ERROR [material_monitor] Sensor re-read failed: timeout waiting for stable reading
2026-04-11 14:30:06 WARN  [material_monitor] Using cached value for channel 2: 0.3kg (age: 1800s)
2026-04-11 14:30:06 WARN  [bar_middleware] /agent/material/all channel_2 returning stale cache data
```

### 故障原因
物料补充后传感器读数需要稳定时间，但系统未等待稳定即读取，读取失败后继续使用旧缓存数据。

### 解决方案
1. 等待 30 秒让传感器读数稳定后手动触发刷新：`curl -X POST http://localhost:8003/agent/material/refresh`
2. 检查缓存配置，确认缓存过期时间设置合理（建议不超过 60s）
3. 查看传感器稳定性：`curl http://localhost:8003/agent/material/channel/2/raw`
4. 若传感器读数持续不稳定，检查物料放置是否均匀，避免偏载
5. 重启物料监控服务强制清除缓存：`sudo systemctl restart material_monitor`

### 预防措施
- 物料补充操作完成后，系统自动等待 30s 再执行传感器读取
- 设置缓存最大有效期，超期数据自动标记为过期并触发重新采集
- 在补充操作界面增加"刷新确认"按钮，方便操作员手动触发更新

---

## 案例 4：物料过期未告警

### 故障现象
运维人员在例行检查时发现部分物料已超过保质期，但系统未发出任何过期告警。查看告警记录，相关告警完全缺失。

### 涉及模块
物料监控服务（过期检测与告警模块）

### 关键日志
```
2026-04-12 00:00:01 INFO  [material_monitor] Running daily expiry check
2026-04-12 00:00:01 ERROR [material_monitor] Failed to load expiry config: FileNotFoundError: /home/smyze/bar_middleware/config/material_expiry.json
2026-04-12 00:00:01 WARN  [material_monitor] Expiry check skipped: configuration missing
2026-04-12 00:00:01 WARN  [material_monitor] No expiry alerts generated for today
```

### 故障原因
物料过期配置文件在上次系统更新时被意外删除或路径变更，导致每日过期检查任务无法加载配置而静默跳过。

### 解决方案
1. 确认配置文件是否存在：`ls /home/smyze/bar_middleware/config/material_expiry.json`
2. 从备份恢复配置文件：`cp /home/smyze/bar_middleware/config/backup/material_expiry.json /home/smyze/bar_middleware/config/`
3. 若无备份，根据物料清单重新创建配置文件，填写各物料的保质期天数
4. 手动触发一次过期检查：`curl -X POST http://localhost:8003/agent/material/check_expiry`
5. 对已过期物料立即下架处理

### 预防措施
- 将物料过期配置文件纳入版本控制，OTA 升级时保护关键配置不被覆盖
- 过期检查任务失败时发送告警，而非静默跳过
- 每次系统升级后自动验证关键配置文件完整性

---

## 案例 5：物料通道堵塞

### 故障现象
出料指令发出后，对应通道无物料输出，但传感器显示该通道仍有余量。订单因出料失败而中止，多次重试均无效。

### 涉及模块
物料出料控制模块（通道电机与出料机构）

### 关键日志
```
2026-04-12 16:45:03 INFO  [material_monitor] Dispensing from channel 4: quantity=30g
2026-04-12 16:45:03 DEBUG [material_monitor] Activating channel 4 motor, duration=2.0s
2026-04-12 16:45:05 WARN  [material_monitor] Channel 4 dispense verification failed: output sensor detected 0g
2026-04-12 16:45:05 ERROR [material_monitor] Dispense failed: channel 4 blocked or motor fault
2026-04-12 16:45:05 ERROR [bar_middleware] Material dispense error on channel 4, aborting order
```

### 故障原因
物料受潮结块或异物进入通道，导致出料口堵塞，电机虽运转但物料无法正常流出。

### 解决方案
1. 立即停止该通道出料：`curl -X POST http://localhost:8003/agent/material/channel/4/disable`
2. 人工打开通道检查口，清除堵塞物料或异物
3. 检查物料状态，若受潮结块则更换新物料
4. 清洁通道后执行测试出料：`curl -X POST http://localhost:8003/agent/material/channel/4/test_dispense`
5. 确认出料正常后重新启用通道：`curl -X POST http://localhost:8003/agent/material/channel/4/enable`

### 预防措施
- 定期检查物料存储环境湿度，保持干燥防止结块
- 每周对各通道执行一次小量测试出料，及时发现堵塞趋势
- 出料口加装防潮密封设计，减少环境湿度影响
