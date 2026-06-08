# 智能充电桩调度计费系统 — API 接口文档

> **版本**: v1.0  
> **基础路径**: `http://localhost:8000`  
> **数据格式**: JSON  
> **编码**: UTF-8

---

## 目录

1. [用户账号](#1-用户账号)
2. [用户认证](#2-用户认证)
3. [充电流程](#3-充电流程)
4. [账单支付](#4-账单支付)
5. [充电桩管理](#5-充电桩管理)
6. [队列管理](#6-队列管理)
7. [调度策略](#7-调度策略)
8. [管理员功能](#8-管理员功能)

---

## 1. 用户账号

### 1.1 创建新账号

创建用户账号和对应车辆信息。

```
POST /api/accounts
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_Id` | string | 是 | 车牌号（也作为登录账号） |
| `userName` | string | 是 | 用户名 |
| `car_Capacity` | number | 是 | 电池容量（kWh），必须 > 0 |

**请求示例：**
```json
{
    "car_Id": "京A12345",
    "userName": "张三",
    "car_Capacity": 60.0
}
```

**成功响应（200）：**
```json
{
    "success": true,
    "user_id": "U20260608093045123456",
    "message": "账号创建成功"
}
```

**失败 — 车牌号已存在：**
```json
{
    "success": false,
    "message": "账号已存在，请直接登录"
}
```

**失败 — 电池容量无效（Pydantic 校验 422）：**
```json
{
    "detail": [
        {"loc": ["body", "car_Capacity"], "msg": "Input should be greater than 0", "type": "greater_than"}
    ]
}
```

---

### 1.2 设置密码

设置/修改登录密码。

```
PUT /api/accounts/{car_id}/password
```

**路径参数：**

| 参数 | 说明 |
|------|------|
| `car_id` | 车牌号 |

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `password` | string | 是 | 密码，长度 >= 6 |

**请求示例：**
```json
{
    "password": "Abc12345"
}
```

**成功响应：**
```json
{
    "success": true,
    "message": "密码设置成功"
}
```

**失败 — 密码太短：**
```json
{
    "success": false,
    "message": "密码长度不能少于6位"
}
```

---

## 2. 用户认证

### 2.1 登录

```
POST /api/auth/login
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_Id` | string | 是 | 车牌号 |
| `password` | string | 是 | 密码 |

**请求示例：**
```json
{
    "car_Id": "京A12345",
    "password": "Abc12345"
}
```

**成功响应：**
```json
{
    "success": true,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVMjAyNjA2MDgwOTMwNDUiLCJjYXJfaWQiOiLkuAoxMjM0NSIsImV4cCI6MTc2Nzc3Nzg0NSwiaWF0IjoxNzY3Nzc3MjQ1fQ.abc123",
    "user_id": "U20260608093045",
    "user_name": "张三",
    "license_plate": "京A12345",
    "membership_level": 1
}
```

**失败 — 密码错误：**
```json
{
    "success": false,
    "message": "账号或密码错误"
}
```

**失败 — 账号已锁定：**
```json
{
    "success": false,
    "message": "账号已锁定，请联系管理员"
}
```

**失败 — 账号不存在：**
```json
{
    "success": false,
    "message": "账号不存在"
}
```

---

## 3. 充电流程

### 3.1 提交充电申请

用户提交充电请求，系统分配最佳充电桩并进入排队区。

```
POST /api/charging/requests
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_Id` | string | 是 | 车牌号 |
| `Request_Amount` | number | 是 | 请求充电量（kWh），必须 > 0 |
| `Request_Mode` | string | 是 | 充电模式：`FAST_CHARGE` / `SLOW_CHARGE` |

**请求示例：**
```json
{
    "car_Id": "京A12345",
    "Request_Amount": 50.0,
    "Request_Mode": "FAST_CHARGE"
}
```

**成功响应：**
```json
{
    "success": true,
    "car_position": 3,
    "car_state": "QUEUED",
    "queue_Num": "P001",
    "request_time": "2026-06-08T09:30:00"
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `car_position` | int | 当前排队位置（1 为最前） |
| `car_state` | string | `QUEUED` 排队中 / `WAITING` 等待区 / `CHARGING` 充电中 |
| `queue_Num` | string | 所在充电桩编号 |
| `request_time` | string | 请求提交时间（ISO 格式） |

**失败 — 无兼容充电桩：**
```json
{
    "success": false,
    "message": "无兼容充电桩可用"
}
```

**失败 — 排队区已满：**
```json
{
    "success": false,
    "message": "排队区已满"
}
```

---

### 3.2 修改充电量

用户在排队区或等待区修改目标充电量。

```
PUT /api/charging/requests/{car_id}/amount
```

**路径参数：** `car_id` — 车牌号

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_Id` | string | 是 | 车牌号 |
| `Amount` | number | 是 | 新充电量（kWh） |

**请求示例：**
```json
{
    "car_Id": "京A12345",
    "Amount": 60.0
}
```

**成功响应：**
```json
{
    "success": true,
    "message": "充电量已更新"
}
```

---

### 3.3 修改充电模式

用户在排队区更换充电模式（快充/慢充）。

```
PUT /api/charging/requests/{car_id}/mode
```

**路径参数：** `car_id` — 车牌号

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_Id` | string | 是 | 车牌号 |
| `Mode` | string | 是 | `FAST_CHARGE` / `SLOW_CHARGE` |

**请求示例：**
```json
{
    "car_Id": "京A12345",
    "Mode": "SLOW_CHARGE"
}
```

**成功响应：**
```json
{
    "success": true,
    "message": "充电模式已更新"
}
```

---

### 3.4 查询排队状态

查询车辆当前在队列中的排队位置和状态。

```
GET /api/charging/requests/{car_id}/state
```

**路径参数：** `car_id` — 车牌号

**成功响应（排队中）：**
```json
{
    "success": true,
    "car_Number_before_position": 3,
    "car_state": "QUEUED",
    "queue_Num": "P001",
    "request_time": "2026-06-08T09:30:00"
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `car_Number_before_position` | int | 前方排队车辆数 |
| `car_state` | string | `QUEUED` / `WAITING` / `CHARGING` / `COMPLETED` / `CANCELLED` |
| `queue_Num` | string | 所在充电桩编号 |
| `request_time` | string | 请求时间 |

**成功响应（充电中）：**
```json
{
    "success": true,
    "car_Number_before_position": 0,
    "car_state": "CHARGING",
    "queue_Num": "P001",
    "request_time": "2026-06-08T09:30:00"
}
```

**失败 — 无活跃请求：**
```json
{
    "success": false,
    "message": "无活跃请求"
}
```

---

### 3.5 开始充电

用户确认开始充电，创建充电会话。

```
POST /api/charging/sessions
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_id` | string | 是 | 车牌号 |
| `ChargePileNum` | string | 是 | 充电桩编号 |

**请求示例：**
```json
{
    "car_id": "京A12345",
    "ChargePileNum": "P001"
}
```

**成功响应：**
```json
{
    "success": true,
    "session_id": "S20260608093045123456",
    "message": "开始充电"
}
```

**失败 — 充电桩不可用：**
```json
{
    "success": false,
    "message": "充电桩当前状态不可用"
}
```

---

### 3.6 查询充电进度

查询充电中的实时进度信息。系统根据已用时间和功率模拟计算已充电量。

```
GET /api/charging/sessions/{car_id}
```

**路径参数：** `car_id` — 车牌号

**成功响应（充电中，按时间模拟）：**
```json
{
    "success": true,
    "car_id": "京A12345",
    "pile_id": "P001",
    "session_id": "S20260608093045123456",
    "current_battery_percentage": 65.0,
    "charged_power_kwh": 30.0,
    "current_power_kw": 110.0,
    "estimated_remaining_minutes": 15.0,
    "current_period_price": 1.2,
    "accumulated_fee": 35.0,
    "start_time": "2026-06-08T09:30:00"
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `current_battery_percentage` | number | 当前电量百分比（0~100） |
| `charged_power_kwh` | number | 已充电量（kWh） |
| `current_power_kw` | number | 当前充电功率（kW） |
| `estimated_remaining_minutes` | number | 预计剩余时间（分钟） |
| `current_period_price` | number | 当前时段电价（元/kWh） |
| `accumulated_fee` | number | 已产生费用（元） |
| `start_time` | string | 充电开始时间 |

**成功响应（已完成）：**
```json
{
    "success": true,
    "car_id": "京A12345",
    "pile_id": "P001",
    "session_id": "S20260607001",
    "charged_power_kwh": 50.0,
    "current_power_kw": 50.0,
    "session_status": "COMPLETED",
    "start_time": "2026-06-07T10:00:00",
    "end_time": "2026-06-07T11:00:00"
}
```

---

### 3.7 结束充电

结束充电（自动完成或用户主动终止），生成账单。

```
DELETE /api/charging/sessions/{car_id}
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ChargingPileNum` | string | 否 | 充电桩编号 |

**成功响应：**
```json
{
    "success": true,
    "bill_id": "B20260608001",
    "total_fee": 58.1,
    "message": "充电结束"
}
```

---

## 4. 账单支付

### 4.1 查看账单

查询指定日期指定用户的充电账单概览。

```
GET /api/bills
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `car_id` | string | 是 | 车牌号 |
| `date` | string | 是 | 日期（YYYY-MM-DD） |

**请求示例：**
```
GET /api/bills?car_id=京A12345&date=2026-06-07
```

**成功响应（有数据）：**
```json
{
    "success": true,
    "bills": [
        {
            "bill_id": "B20260607001",
            "car_id": "京A12345",
            "date": "2026-06-07",
            "pile_id": "P001",
            "charge_amount": 45.5,
            "charge_duration_minutes": 60.0,
            "start_time": "2026-06-07T10:30:00",
            "end_time": "2026-06-07T11:30:00",
            "total_charge_fee": 45.6,
            "total_service_fee": 12.5,
            "total_fee": 58.1
        }
    ]
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `bill_id` | string | 账单编号 |
| `charge_amount` | number | 充电量（kWh） |
| `charge_duration_minutes` | number | 充电时长（分钟） |
| `total_charge_fee` | number | 电费合计（元） |
| `total_service_fee` | number | 服务费合计（元） |
| `total_fee` | number | 总费用（元） = 电费 + 服务费 |

**成功响应（无数据）：**
```json
{
    "success": true,
    "bills": []
}
```

---

### 4.2 查看详单

获取账单的分时段费用明细（峰/平/谷三段拆分）。

```
GET /api/bills/{bill_id}/details
```

**路径参数：** `bill_id` — 账单编号

**成功响应：**
```json
{
    "success": true,
    "bill_id": "B20260607001",
    "car_id": "京A12345",
    "date": "2026-06-07",
    "pile_id": "P001",
    "charge_amount": 45.5,
    "charge_duration_minutes": 60.0,
    "start_time": "2026-06-07T10:30:00",
    "end_time": "2026-06-07T11:30:00",
    "payment_status": "UNPAID",
    "periods": [
        {
            "period_name": "peak",
            "period_start": "2026-06-07T10:30:00",
            "period_end": "2026-06-07T11:00:00",
            "charge_kwh": 20.0,
            "unit_price": 1.2,
            "charge_fee": 24.0,
            "service_fee": 5.0,
            "subtotal_fee": 29.0
        },
        {
            "period_name": "normal",
            "period_start": "2026-06-07T11:00:00",
            "period_end": "2026-06-07T11:30:00",
            "charge_kwh": 25.5,
            "unit_price": 0.8,
            "charge_fee": 20.4,
            "service_fee": 7.5,
            "subtotal_fee": 27.9
        }
    ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `period_name` | string | 时段：`peak` / `normal` / `valley` |
| `charge_kwh` | number | 该时段充电量（kWh） |
| `unit_price` | number | 该时段电价（元/kWh） |
| `charge_fee` | number | 该时段电费 |
| `service_fee` | number | 该时段服务费 |
| `subtotal_fee` | number | 小计 = charge_fee + service_fee |
| `payment_status` | string | `UNPAID` / `PAID` / `REFUNDED` |

---

### 4.3 支付账单

模拟支付流程，将账单标记为已支付并生成支付订单。

```
POST /api/payments/{bill_id}/pay
```

**路径参数：** `bill_id` — 账单编号

**成功响应（首次支付）：**
```json
{
    "success": true,
    "bill_id": "B20260607001",
    "payment_status": "PAID",
    "order_id": "P20260608001",
    "total_amount": 110.0
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `payment_status` | string | `PAID` |
| `order_id` | string | 支付订单编号 |
| `total_amount` | number | 支付金额（元） |

**成功响应（重复支付）：**
```json
{
    "success": true,
    "bill_id": "B20260607001",
    "payment_status": "PAID",
    "message": "账单已支付"
}
```

**失败 — 账单不存在：**
```json
{
    "success": false,
    "message": "账单不存在"
}
```

---

## 5. 充电桩管理

### 5.1 启动充电桩电源

开启充电桩电源，使其进入可用状态。

```
POST /api/piles/{pile_id}/power/on
```

**路径参数：** `pile_id` — 充电桩编号（如 P001）

**成功响应：**
```json
{
    "success": true,
    "message": "充电桩电源已开启"
}
```

**失败 — 充电桩不存在：**
```json
{
    "success": false,
    "message": "充电桩不存在"
}
```

---

### 5.2 设置充电桩参数

设置充电桩的计费规则和三时段电价数据。

```
PUT /api/piles/{pile_id}/parameters
```

**路径参数：** `pile_id` — 充电桩编号

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pile_Id` | string | 是 | 充电桩编号 |
| `peak_price` | number | 是 | 峰时电价（元/kWh） |
| `normal_price` | number | 是 | 平时电价（元/kWh） |
| `valley_price` | number | 是 | 谷时电价（元/kWh） |
| `base_service_fee` | number | 否 | 基础服务费（元），默认 5.0 |
| `time_coefficient` | number | 否 | 时长系数（元/分钟），默认 0.5 |

**请求示例：**
```json
{
    "pile_Id": "P001",
    "peak_price": 1.5,
    "normal_price": 1.0,
    "valley_price": 0.5,
    "base_service_fee": 5.0,
    "time_coefficient": 0.5
}
```

**成功响应：**
```json
{
    "success": true,
    "message": "参数设置成功"
}
```

---

### 5.3 运行充电桩

将充电桩从"可用"切换为"运行中"，使其可接受充电请求。

```
POST /api/piles/{pile_id}/run
```

**路径参数：** `pile_id` — 充电桩编号

**成功响应：**
```json
{
    "success": true,
    "message": "充电桩已进入运行状态"
}
```

---

### 5.4 关闭充电桩

关闭充电桩电源。如正在充电中则拒绝操作。

```
POST /api/piles/{pile_id}/power/off
```

**路径参数：** `pile_id` — 充电桩编号

**成功响应：**
```json
{
    "success": true,
    "message": "充电桩已关闭"
}
```

**失败 — 正在充电中：**
```json
{
    "success": false,
    "message": "充电桩正在使用中，无法关机"
}
```

---

### 5.5 查看充电桩状态

查看充电桩的实时工作状态和累计统计数据。

```
GET /api/piles/{pile_id}/state
```

**路径参数：** `pile_id` — 充电桩编号

**成功响应（运行中）：**
```json
{
    "success": true,
    "pile_id": "P001",
    "working_state": "RUNNING",
    "total_charge_num": 125,
    "total_charge_time": 4560.5,
    "total_capacity": 8520.0,
    "current_charging_count": 2,
    "status": "CHARGING"
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `working_state` | string | 工作状态：`RUNNING` / `AVAILABLE` / `CHARGING` / `CLOSED` / `FAULT` / `QUEUEING` |
| `total_charge_num` | int | 累计充电次数 |
| `total_charge_time` | number | 累计充电时长（分钟） |
| `total_capacity` | number | 累计充电容量（kWh） |
| `current_charging_count` | int | 当前正在充电的车辆数 |
| `status` | string | 数据库原始状态 |

**失败 — 充电桩不存在：**
```json
{
    "success": false,
    "message": "充电桩 P999 不存在"
}
```

---

## 6. 队列管理

### 6.1 查看队列状态

管理员查看指定充电桩队列中的车辆详情。

```
GET /api/queues/state
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `queuelist` | string | 是 | 充电桩编号列表，逗号分隔 |

**请求示例：**
```
GET /api/queues/state?queuelist=P001,P002
```

**成功响应：**
```json
{
    "success": true,
    "queues": [
        {
            "pile_id": "P001",
            "zone_type": "QUEUE_AREA",
            "vehicles": [
                {
                    "car_id": "京A12345",
                    "battery_capacity_kwh": 60.0,
                    "request_amount_kwh": 50.0,
                    "wait_minutes": 15.0
                },
                {
                    "car_id": "京B67890",
                    "battery_capacity_kwh": 80.0,
                    "request_amount_kwh": 30.0,
                    "wait_minutes": 8.0
                }
            ]
        }
    ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `pile_id` | string | 充电桩编号 |
| `zone_type` | string | 区域类型 |
| `car_id` | string | 车牌号 |
| `battery_capacity_kwh` | number | 电池容量（kWh） |
| `request_amount_kwh` | number | 请求电量（kWh） |
| `wait_minutes` | number | 已等待时间（分钟） |

---

## 7. 调度策略

### 7.1 获取当前策略

获取当前激活的分配策略和故障策略。

```
GET /api/strategies
```

**成功响应：**
```json
{
    "success": true,
    "current_algorithm": "SHORTEST_TOTAL_TIME",
    "current_fault_strategy": "TIME_ORDER",
    "available_algorithms": ["SHORTEST_TOTAL_TIME", "BATCH_SHORTEST_TIME"],
    "available_fault_strategies": [
        "PRIORITY", "TIME_ORDER", "FAULT_RECOVERY",
        "SHORTEST_TOTAL_TIME", "BATCH_SHORTEST_TIME"
    ]
}
```

| 返回字段 | 说明 |
|----------|------|
| `current_algorithm` | 当前分配策略 |
| `current_fault_strategy` | 当前故障策略 |
| `available_algorithms` | 可选分配策略列表 |
| `available_fault_strategies` | 可选故障策略列表 |

**策略标识符对照：**

| 标识符 | 策略 | 类型 |
|--------|------|------|
| `SHORTEST_TOTAL_TIME` | 单次调度最短时长 | 分配/故障 |
| `BATCH_SHORTEST_TIME` | 批量调度最短时长（匈牙利算法）| 分配/故障 |
| `PRIORITY` | 优先级调度 | 故障 |
| `TIME_ORDER` | 时间顺序调度 | 故障 |
| `FAULT_RECOVERY` | 充电中故障恢复 | 故障 |

---

### 7.2 切换分配策略

运行时切换正常分配策略。

```
PUT /api/strategies/dispatch
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `strategy_type` | string | 是 | `SHORTEST_TOTAL_TIME` / `BATCH_SHORTEST_TIME` |

**请求示例：**
```json
{
    "strategy_type": "BATCH_SHORTEST_TIME"
}
```

**成功响应：**
```json
{
    "success": true,
    "current_algorithm": "BATCH_SHORTEST_TIME"
}
```

**失败 — 未知策略：**
```json
{
    "success": false,
    "message": "未知策略: INVALID"
}
```

---

### 7.3 切换故障策略

运行时切换故障处理策略。

```
PUT /api/strategies/fault
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `strategy_type` | string | 是 | `PRIORITY` / `TIME_ORDER` / `FAULT_RECOVERY` / `SHORTEST_TOTAL_TIME` / `BATCH_SHORTEST_TIME` |

**请求示例：**
```json
{
    "strategy_type": "PRIORITY"
}
```

**成功响应：**
```json
{
    "success": true,
    "current_fault_strategy": "PRIORITY"
}
```

---

## 8. 管理员功能

### 8.1 移动车辆位置

管理员将车辆移动到任何未满队列的任何区域的任意位置。覆盖 UC-16。

```
PUT /api/admin/vehicles/{car_id}/move
```

**路径参数：** `car_id` — 车牌号

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target_pile_id` | string | 是 | 目标充电桩编号 |
| `target_zone` | string | 是 | 目标区域：`QUEUE_AREA` / `WAITING_AREA` / `CHARGING_AREA` |
| `target_position` | int | 否 | 目标位置序号，默认 1 |

**请求示例：**
```
PUT /api/admin/vehicles/京A12345/move?target_pile_id=P002&target_zone=QUEUE_AREA&target_position=2
```

**成功响应：**
```json
{
    "success": true,
    "car_id": "京A12345",
    "new_pile_id": "P002",
    "new_zone": "QUEUE_AREA",
    "new_position": 2,
    "message": "车辆已移动"
}
```

**失败 — 目标区域已满：**
```json
{
    "success": false,
    "message": "WAITING_AREA 已满"
}
```

**失败 — 车辆无活跃请求：**
```json
{
    "success": false,
    "message": "该车辆无活跃充电请求"
}
```

**失败 — 充电桩不存在：**
```json
{
    "success": false,
    "message": "充电桩 P999 不存在"
}
```

---

### 8.2 生成运营报表

生成充电站运营报表，包括充电量、收入、利用率等关键指标。覆盖 UC-20。

```
GET /api/admin/reports
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `start_date` | string | 否 | 开始日期 YYYY-MM-DD，默认当月第一天 |
| `end_date` | string | 否 | 结束日期 YYYY-MM-DD，默认当天 |

**请求示例：**
```
GET /api/admin/reports?start_date=2026-01-01&end_date=2026-06-30
```

**成功响应：**
```json
{
    "success": true,
    "report": {
        "period": {
            "start": "2026-01-01",
            "end": "2026-06-30"
        },
        "summary": {
            "total_charge_capacity_kwh": 8520.0,
            "total_revenue": 58000.0,
            "total_sessions": 125,
            "utilization_rate": 0.45
        },
        "pile_details": [
            {
                "pile_id": "P001",
                "pile_name": "快充桩-01",
                "type": "fast_charge",
                "max_power_kw": 120.0,
                "status": "CHARGING",
                "total_charge_num": 125,
                "total_capacity_kwh": 8520.0,
                "charge_time_minutes": 4560.5,
                "current_charging_count": 2
            },
            {
                "pile_id": "P002",
                "pile_name": "快充桩-02",
                "type": "fast_charge",
                "max_power_kw": 120.0,
                "status": "RUNNING",
                "total_charge_num": 98,
                "total_capacity_kwh": 6800.0,
                "charge_time_minutes": 3200.0,
                "current_charging_count": 1
            }
        ]
    }
}
```

| 报表字段 | 类型 | 说明 |
|----------|------|------|
| `period.start` | string | 统计开始日期 |
| `period.end` | string | 统计结束日期 |
| `summary.total_charge_capacity_kwh` | number | 总充电量（kWh） |
| `summary.total_revenue` | number | 总收入（元） |
| `summary.total_sessions` | int | 总充电次数 |
| `summary.utilization_rate` | number | 充电桩利用率（0~1） |
| `pile_details` | array | 各充电桩明细 |

---

## 附录：状态码说明

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 操作成功（即使业务处理失败也返回 200，通过 `success` 字段区分） |
| 422 | 请求参数校验失败（Pydantic 校验未通过） |
| 404 | 资源不存在 |

所有业务端点的响应都包含 `success` 字段：

- `true` — 业务处理成功
- `false` — 业务处理失败（具体原因在 `message` 字段）
