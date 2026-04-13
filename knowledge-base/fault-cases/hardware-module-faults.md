# 硬件模块故障案例

## 案例 1：制冰机不出冰（压缩机过热保护）

### 故障现象
饮品制作流程中加冰步骤失败，设备报告制冰机无冰可用。检查制冰机发现压缩机已停机，机身温度明显偏高，制冰机进入保护状态。

### 涉及模块
制冰机控制模块（/ice/machine/status API）

### 关键日志
```
2026-04-10 13:20:05 WARN  [ice_machine] Compressor temperature: 85°C, threshold: 80°C
2026-04-10 13:20:05 ERROR [ice_machine] Overheat protection triggered: compressor shutdown
2026-04-10 13:20:06 ERROR [bar_middleware] GET /ice/machine/status: {"status": "error", "code": "OVERHEAT_PROTECTION", "ice_available": false}
2026-04-10 13:20:06 ERROR [bar_middleware] Ice machine unavailable, cannot fulfill ice request
```

### 故障原因
制冰机冷凝器散热不良（积尘堵塞或环境温度过高），导致压缩机持续高温运行，触发过热保护自动停机。

### 解决方案
1. 查询制冰机状态：`curl http://192.168.42.1/ice/machine/status`
2. 关闭制冰机电源，等待压缩机冷却至少 30 分钟
3. 清洁冷凝器散热格栅，用压缩空气吹除积尘
4. 检查设备安装位置通风是否良好，确保冷凝器侧面留有至少 15cm 空间
5. 冷却后重新上电，观察压缩机温度是否恢复正常：`curl http://192.168.42.1/ice/machine/status`

### 预防措施
- 每月清洁一次冷凝器散热格栅，防止积尘堵塞
- 确保设备安装环境温度不超过 35°C
- 配置压缩机温度监控，超过 75°C 时提前告警

---

## 案例 2：咖啡机水温不达标

### 故障现象
咖啡制作完成后口感异常，顾客反映咖啡温度偏低。系统日志显示咖啡机出水温度低于设定值，加热模块未能将水温提升至目标温度。

### 涉及模块
咖啡机控制模块（/coffee/machine/status API）

### 关键日志
```
2026-04-11 09:10:22 WARN  [coffee_machine] Water temperature: 78°C, target: 92°C
2026-04-11 09:10:22 WARN  [coffee_machine] Heating element output at 100%, temperature not reaching target
2026-04-11 09:10:23 ERROR [bar_middleware] GET /coffee/machine/status: {"water_temp": 78, "target_temp": 92, "status": "temp_low"}
2026-04-11 09:10:25 WARN  [coffee_machine] Brew executed with suboptimal temperature: 78°C
```

### 故障原因
加热管水垢积累导致热效率下降，或加热元件老化功率不足，无法将水温加热至目标温度。

### 解决方案
1. 查询咖啡机当前状态：`curl http://192.168.42.1/coffee/machine/status`
2. 执行除垢程序：按照咖啡机手册使用专用除垢剂运行除垢循环
3. 除垢后检查水温是否恢复正常，观察加热时间是否缩短
4. 若除垢后仍不达标，检查加热元件电阻值，判断是否需要更换
5. 更换加热元件后重新校准温度传感器

### 预防措施
- 每 3 个月执行一次除垢保养，水质较硬地区缩短至每月一次
- 监控加热至目标温度所需时间，时间持续增长时提前预警
- 安装水质过滤器，减少水垢生成速度

---

## 案例 3：杯子机卡杯

### 故障现象
出杯指令发出后，杯子机电机运转但无杯子输出，系统报告出杯失败。检查杯子机发现杯子在出杯通道中卡住，后续杯子堆积无法下落。

### 涉及模块
杯子机控制模块（出杯机构与传感器）

### 关键日志
```
2026-04-11 16:05:33 INFO  [cup_machine] Dispensing cup, channel=large
2026-04-11 16:05:33 DEBUG [cup_machine] Motor activated, duration=1.5s
2026-04-11 16:05:35 WARN  [cup_machine] Cup exit sensor not triggered after dispense
2026-04-11 16:05:35 ERROR [cup_machine] Cup dispense failed: no cup detected at output
2026-04-11 16:05:35 ERROR [bar_middleware] Cup machine error: JAM_DETECTED, aborting order
```

### 故障原因
杯子变形或尺寸偏差导致在出杯通道中卡住，或通道内有异物阻碍杯子正常下落。

### 解决方案
1. 立即停止出杯机电机：`curl -X POST http://192.168.42.1/cup/machine/stop`
2. 打开杯子机检修盖，手动取出卡住的杯子
3. 检查通道内是否有异物，清理干净
4. 检查剩余杯子规格是否符合要求，取出变形杯子
5. 关闭检修盖后执行测试出杯：`curl -X POST http://192.168.42.1/cup/machine/test_dispense`

### 预防措施
- 补充杯子时检查杯子质量，剔除变形或尺寸不符的杯子
- 每周清洁出杯通道，防止异物积累
- 配置连续出杯失败 2 次自动暂停并告警，避免电机过载

---

## 案例 4：扣盖机对位失败

### 故障现象
饮品制作完成后，扣盖机执行扣盖动作时报告对位失败，杯盖未能正确扣合。系统中止当前订单，扣盖机停留在错误位置。

### 涉及模块
扣盖机控制模块（对位传感器与执行机构）

### 关键日志
```
2026-04-12 11:30:44 INFO  [lid_machine] Starting lid placement sequence
2026-04-12 11:30:44 DEBUG [lid_machine] Cup detected at position sensor, proceeding
2026-04-12 11:30:45 ERROR [lid_machine] Alignment check failed: cup offset 8mm from center (max: 3mm)
2026-04-12 11:30:45 ERROR [lid_machine] Lid placement aborted to prevent spill
2026-04-12 11:30:45 ERROR [bar_middleware] Lid machine alignment error, order aborted
```

### 故障原因
杯子放置位置偏移超出扣盖机允许的对位容差，通常由机械臂放杯位置漂移或杯托固定件松动引起。

### 解决方案
1. 查询扣盖机状态：`curl http://192.168.42.1/lid/machine/status`
2. 检查杯托固定件是否松动，重新紧固螺丝
3. 重新校准机械臂放杯位置：`curl -X POST http://192.168.42.1/RobotArm/Dev/calibrate_cup_position`
4. 手动放置杯子测试扣盖机对位：`curl -X POST http://192.168.42.1/lid/machine/test`
5. 调整扣盖机对位容差参数（如机械臂精度允许）：编辑配置中 `alignment_tolerance_mm` 参数

### 预防措施
- 每周检查杯托和扣盖机固定件的紧固状态
- 定期校准机械臂放杯位置，防止累积误差
- 监控对位偏移量趋势，偏移量持续增大时提前预警

---

## 案例 5：冷凝器温度过高告警

### 故障现象
设备监控面板出现冷凝器高温告警，制冷系统效率下降。若不及时处理，将触发压缩机过热保护导致制冷停机。

### 涉及模块
制冷系统冷凝器温度监控模块

### 关键日志
```
2026-04-12 14:55:01 WARN  [cooling_system] Condenser temperature: 62°C, warning threshold: 60°C
2026-04-12 14:55:01 WARN  [cooling_system] Cooling efficiency degraded: 15% below nominal
2026-04-12 14:55:02 WARN  [bar_middleware] GET /ice/machine/status: condenser_temp=62, status=warning
2026-04-12 14:55:05 WARN  [cooling_system] Condenser fan speed at maximum, temperature still rising
```

### 故障原因
冷凝器翅片积尘严重导致散热效率下降，或冷凝器风扇转速不足，无法有效带走热量。

### 解决方案
1. 查询冷凝器当前温度：`curl http://192.168.42.1/ice/machine/status`
2. 检查冷凝器风扇是否正常运转，转速是否达到额定值
3. 关机后用压缩空气清洁冷凝器翅片，彻底清除积尘
4. 检查设备周围通风环境，移除阻挡散热的障碍物
5. 清洁完成后重新上电，监控冷凝器温度是否下降至正常范围（低于 55°C）

### 预防措施
- 每月清洁冷凝器翅片，高粉尘环境下每两周清洁一次
- 确保设备安装位置符合通风要求，冷凝器侧不得紧贴墙壁
- 配置冷凝器温度趋势监控，温度持续上升时提前安排保养
