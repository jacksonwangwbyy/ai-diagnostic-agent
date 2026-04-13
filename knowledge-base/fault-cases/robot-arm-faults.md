# 机械臂故障案例

## 案例 1：机械臂归零失败

### 故障现象
设备开机初始化时，机械臂归零动作未完成，系统报告初始化超时。控制界面显示机械臂状态为"未就绪"，所有后续动作指令被拒绝执行。

### 涉及模块
机械臂控制服务（/RobotArm/Dev/status API，192.168.42.1）

### 关键日志
```
2026-04-10 07:30:05 INFO  [robot_arm] Starting homing sequence
2026-04-10 07:30:05 DEBUG [robot_arm] Sending homing command to axis 1, 2, 3
2026-04-10 07:30:35 ERROR [robot_arm] Homing timeout: axis 2 did not reach home position within 30s
2026-04-10 07:30:35 ERROR [bar_middleware] GET /RobotArm/Dev/status returned: {"status": "error", "code": "HOMING_FAILED"}
2026-04-10 07:30:35 WARN  [bar_middleware] Robot arm not ready, blocking all action requests
```

### 故障原因
机械臂第 2 轴限位传感器信号异常或机械卡阻，导致归零动作无法到达原点位置触发限位开关。

### 解决方案
1. 检查机械臂是否有物理卡阻，手动轻推各轴确认活动自如
2. 查询轴状态：`curl http://192.168.42.1:8001/RobotArm/Dev/axis_status`
3. 检查限位传感器接线是否松动，重新插拔传感器连接器
4. 清除错误状态并重试归零：`curl -X POST http://192.168.42.1:8001/RobotArm/Dev/reset && curl -X POST http://192.168.42.1:8001/RobotArm/Dev/home`
5. 若仍失败，重启机械臂控制服务：`sudo systemctl restart robot_arm_service`

### 预防措施
- 每日开机前自动执行归零自检，失败时记录并告警
- 定期检查限位传感器和机械导轨，清洁润滑
- 配置归零失败后自动重试 3 次，超过次数再上报故障

---

## 案例 2：手爪抓取检测异常（物体掉落）

### 故障现象
机械臂执行取杯动作后，传感器未检测到抓取成功，系统报告抓取失败并中止当前订单流程。实际观察发现杯子已被抓起但随即掉落。

### 涉及模块
机械臂手爪模块（抓取力控制与传感器反馈）

### 关键日志
```
2026-04-10 11:22:14 INFO  [robot_arm] Executing grip action: target=cup, position=(120, 45, 230)
2026-04-10 11:22:15 DEBUG [robot_arm] Grip force applied: 35N, expected: 40-60N
2026-04-10 11:22:15 WARN  [robot_arm] Grip sensor feedback: object_detected=false after grip
2026-04-10 11:22:15 ERROR [robot_arm] Grip verification failed: no object in gripper
2026-04-10 11:22:15 ERROR [bar_middleware] Action PICK_CUP failed: gripper reported empty
```

### 故障原因
手爪气压不足导致夹持力低于设定值，或抓取位置偏移导致未能有效夹持杯子，传感器误判为未抓取。

### 解决方案
1. 检查气压系统压力：确认气源压力在 0.4-0.6 MPa 范围内
2. 查看手爪传感器校准值：`curl http://192.168.42.1:8001/RobotArm/Dev/gripper/calibration`
3. 重新校准抓取位置：`curl -X POST http://192.168.42.1:8001/RobotArm/Dev/gripper/calibrate`
4. 调整抓取力参数：编辑机械臂配置文件中的 `grip_force` 参数，增加至 50N
5. 执行测试抓取动作验证：`curl -X POST http://192.168.42.1:8001/RobotArm/Dev/test_grip`

### 预防措施
- 每周检查气压系统，确保气管无泄漏
- 定期（每月）重新校准手爪抓取位置和力度参数
- 配置连续抓取失败 3 次自动暂停并告警，避免反复掉落损坏杯子

---

## 案例 3：机械臂运动超时

### 故障现象
机械臂在执行移动指令后长时间未到达目标位置，系统等待超时后报错并停止当前任务。机械臂停留在中间位置，需要人工干预复位。

### 涉及模块
机械臂运动控制模块（轨迹规划与执行）

### 关键日志
```
2026-04-11 15:44:02 INFO  [robot_arm] Moving to position: (300, 120, 180), timeout=15s
2026-04-11 15:44:02 DEBUG [robot_arm] Trajectory planned, executing 3-axis movement
2026-04-11 15:44:17 ERROR [robot_arm] Motion timeout: target not reached within 15s
2026-04-11 15:44:17 ERROR [robot_arm] Current position: (285, 118, 180), delta: (15, 2, 0)
2026-04-11 15:44:17 ERROR [bar_middleware] RobotArm motion failed: MOTION_TIMEOUT, aborting task
```

### 故障原因
机械臂导轨润滑不足或负载过重导致运动速度下降，未能在超时时间内到达目标位置。

### 解决方案
1. 立即停止机械臂：`curl -X POST http://192.168.42.1:8001/RobotArm/Dev/stop`
2. 手动将机械臂移至安全位置后执行归零：`curl -X POST http://192.168.42.1:8001/RobotArm/Dev/home`
3. 检查导轨润滑状态，必要时添加润滑油
4. 适当增加运动超时时间：编辑配置文件中 `motion_timeout` 参数（建议 20s）
5. 降低运动速度参数 `max_velocity` 10-20%，重新测试

### 预防措施
- 每月定期润滑机械臂导轨和关节
- 监控运动完成时间趋势，时间持续增长时提前预警
- 避免超出机械臂额定负载范围操作

---

## 案例 4：机械臂通信断开

### 故障现象
中间件突然无法获取机械臂状态，所有机械臂控制指令返回连接错误。机械臂本体指示灯显示正常，但网络通信中断。

### 涉及模块
机械臂控制服务（TCP/IP 通信，192.168.42.1:8001）

### 关键日志
```
2026-04-11 18:30:11 ERROR [bar_middleware] GET /RobotArm/Dev/status failed: ConnectionRefusedError
2026-04-11 18:30:11 ERROR [bar_middleware] Robot arm unreachable at 192.168.42.1:8001
2026-04-11 18:30:14 WARN  [bar_middleware] Retry 1/3 failed: robot arm connection refused
2026-04-11 18:30:17 WARN  [bar_middleware] Retry 2/3 failed: robot arm connection refused
2026-04-11 18:30:20 ERROR [bar_middleware] Robot arm communication lost after 3 retries, disabling arm
```

### 故障原因
机械臂控制器内部服务崩溃或网络接口异常，导致 8001 端口不再响应连接请求。

### 解决方案
1. 确认网络连通性：`ping 192.168.42.1`
2. 检查端口是否开放：`nc -zv 192.168.42.1 8001`
3. SSH 登录机械臂控制器检查服务状态：`ssh smyze@192.168.42.1 "sudo systemctl status robot_arm_service"`
4. 重启机械臂控制服务：`ssh smyze@192.168.42.1 "sudo systemctl restart robot_arm_service"`
5. 重启后验证通信恢复：`curl http://192.168.42.1:8001/RobotArm/Dev/status`

### 预防措施
- 配置机械臂控制服务的 watchdog，服务崩溃后自动重启
- 中间件实现通信断开自动重连机制，断开后每 30s 尝试重连
- 部署网络监控，192.168.42.1:8001 不可达时立即告警

---

## 案例 5：机械臂碰撞保护触发

### 故障现象
机械臂在运动过程中突然停止，控制界面显示"碰撞保护已触发"。机械臂进入锁定状态，拒绝执行任何新指令，需要人工确认后才能恢复。

### 涉及模块
机械臂安全保护模块（碰撞检测与力矩监控）

### 关键日志
```
2026-04-12 09:15:33 INFO  [robot_arm] Executing move to dispensing position
2026-04-12 09:15:34 ERROR [robot_arm] Collision detected: joint torque exceeded threshold on axis 3
2026-04-12 09:15:34 ERROR [robot_arm] Torque reading: 8.5Nm, threshold: 6.0Nm
2026-04-12 09:15:34 ERROR [robot_arm] EMERGENCY STOP triggered, all axes locked
2026-04-12 09:15:34 ERROR [bar_middleware] Robot arm collision protection activated, status=LOCKED
```

### 故障原因
机械臂运动路径上存在障碍物（如错位的杯子或设备部件），或关节力矩阈值设置过低，导致碰撞保护误触发。

### 解决方案
1. 检查机械臂周围是否有障碍物，清除后确认工作区域安全
2. 查看碰撞详情：`curl http://192.168.42.1:8001/RobotArm/Dev/collision_report`
3. 人工确认安全后解除锁定：`curl -X POST http://192.168.42.1:8001/RobotArm/Dev/unlock`
4. 执行归零重置：`curl -X POST http://192.168.42.1:8001/RobotArm/Dev/home`
5. 若为误触发，适当调整力矩阈值：编辑配置中 `collision_torque_threshold` 参数

### 预防措施
- 定期检查机械臂工作区域内的固定部件位置，确保无偏移
- 合理设置碰撞力矩阈值，既能保护设备又避免频繁误触发
- 记录每次碰撞保护触发的位置和力矩数据，分析规律性问题
