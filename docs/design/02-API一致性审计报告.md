# API 接口一致性审计报告

> **审计时间**：2026-06-15  
> **基准文档**：`docs/design/01-API接口说明.md` (v1.0)  
> **审计范围**：`backend/` 全部路由层和服务层代码  
> **状态**：已发现 13 类需操作事项

---

## 总体结论

整体框架（认证、充电桩、充电会话核心流程、账单）与文档匹配度较高，**21 个接口完全一致**。问题集中在管理端接口和报表接口，共发现 **13 项需操作事项**，其中严重 7 项、中等 4 项、轻微 2 项。

---

## 需操作事项清单

---

### P0-01: `/admin/config` GET 响应结构与文档不一致

**位置**：`backend/service/admin/service.py:get_all_configs()`  
**问题**：文档要求 `schedulingAlgorithm`、`baseServiceFee` 为顶层字段，但代码将它们嵌套在 `globalConfigs` 对象内。电价时段字段名 `startTime`/`endTime` 与文档的 `start`/`end` 不符。响应中多了 `id`、`priority`、`tierName` 等未定义字段。

**文档要求**：
```json
{
  "schedulingAlgorithm": "shortest_time_single",
  "baseServiceFee": 5.0,
  "electricityPrices": [
    { "periodName": "峰时", "start": "08:00", "end": "11:00", "pricePerKwh": 1.2 }
  ],
  "serviceFeeTiers": [
    { "minMinutes": 0, "maxMinutes": 60, "ratePerMinute": 0.15 }
  ]
}
```

**代码实际**：
```json
{
  "globalConfigs": { "schedulingAlgorithm": "...", "baseServiceFee": "5.0" },
  "electricityPrices": [
    { "id": 1, "periodName": "峰时", "startTime": "08:00", "endTime": "11:00", "pricePerKwh": 1.2, "priority": 0 }
  ],
  "serviceFeeTiers": [
    { "id": 1, "tierName": "0-60分钟", "minMinutes": 0, "maxMinutes": 60, "ratePerMinute": 0.15 }
  ]
}
```

**操作**：重写 `get_all_configs()` 响应组装逻辑，扁平化为文档定义的顶层结构，修正字段命名，移除多余字段。

---

### P0-02: `/admin/config` PUT 请求格式与文档不一致

**位置**：`backend/api/admin/config/router.py:admin_update_config()` + `backend/service/admin/service.py:update_configs()`

**问题**：文档要求 PUT 请求以顶层字段发送（`schedulingAlgorithm`、`baseServiceFee`、`electricityPrices`、`serviceFeeTiers`），但 `update_configs()` 函数期望它们嵌套在 `globalConfigs` 内。电价字段同样使用 `startTime`/`endTime` 而非 `start`/`end`。

**操作**：
1. 修改 `update_configs()` 接受文档定义的扁平化请求格式
2. 电价时段字段接受 `start`/`end` 命名
3. `serviceFeeTiers` 接受 `tierName`、`minMinutes`、`maxMinutes`、`ratePerMinute`

---

### P0-03: `/admin/sessions` GET 响应字段命名和结构与文档不一致

**位置**：`backend/service/admin/service.py:list_all_sessions()`

**问题**：
- `list[].id` → 文档要求 `sessionId`
- 平铺的 `userId`、`licensePlate` → 文档要求嵌套 `user: {id, licensePlate}`
- 平铺的 `stationId`、`stationName` → 文档要求嵌套 `station: {id, name}`
- 缺失 `progress` 字段
- 多余 `zone`、`advanceReady` 字段

**操作**：按文档重构响应结构，添加 `progress` 计算，移除多余字段。

---

### P0-04: `/admin/sessions/:id` GET 响应结构与文档不一致

**位置**：`backend/service/admin/service.py:get_admin_session_detail()`

**问题**：文档要求包含 `user: {id, licensePlate}` 嵌套对象 + 同 `GET /sessions/:id` 的所有字段。代码返回平铺字段。

**操作**：重构为嵌套 `user`/`station` 结构，补充 `protocol`、`currentFee`、`bill` 等来自 `GET /sessions/:id` 的标准字段。

---

### P0-05: `/admin/bills` GET 响应字段结构与文档不一致

**位置**：`backend/service/admin/service.py:list_all_bills()`

**问题**：
- 平铺 `userId`、`licensePlate` → 文档要求嵌套 `user: {id, licensePlate}`
- 平铺 `stationName` → 文档要求嵌套 `station: {id, name}`
- 多余字段 `electricityFee`、`serviceFee`、`totalEnergyKwh`
- 文档要求的 `chargedEnergyKwh` → 代码使用 `totalEnergyKwh`

**操作**：按文档重构响应结构，清理多余字段。

---

### P0-06: `/admin/stations/:id/emergency-stop` POST 响应字段与文档不一致

**位置**：`backend/service/station/service.py:emergency_stop_station()`

**问题**：
- `status` 返回 `"error"` → 文档要求 `"stopped"`
- 文档要求返回 `chargingSessions` 数组 → 代码缺失
- 代码返回了文档未定义的 `failedSessions`

**操作**：修正 `status` 值，添加 `chargingSessions`（列出仍在充电的车辆），移除 `failedSessions` 或将其纳入文档。

---

### P0-07: `/admin/queues/move` PUT 请求字段缺失

**位置**：`backend/api/admin/queues/router.py:MoveRequest`

**问题**：文档要求包含 `targetZone` 字段（`queue`），代码的 `MoveRequest` 未定义该字段。

**操作**：在 `MoveRequest` 中添加 `target_zone: str = Field(alias="targetZone")`，并在 `move_session_to_station()` 中使用该参数验证和写入目标区域。

---

### P1-01: `/sessions/:id` GET 多余字段

**位置**：`backend/api/sessions/router.py:_build_session_detail()`

**问题**：响应中返回了 `advanceReady` 字段，文档中未定义此字段。

**操作**：移除 `_build_session_detail()` 返回值中的 `advanceReady` 字段，或将其更新到 API 文档中。

---

### P1-02: `/sessions/:id/cancel` POST 排队取消缺少 `bill: null`

**位置**：`backend/api/sessions/router.py:_handle_reject()` (queued 分支)

**问题**：文档示例中排队取消返回 `"bill": null`，但代码响应中未包含 `bill` 字段。

**操作**：在排队取消的响应中添加 `"bill": None`。

---

### P1-03: `/sessions/:id/confirm-charging` POST 排队态拒绝缺少 `bill: null`

**位置**：`backend/api/sessions/router.py:_handle_reject()` (queued 分支)

**问题**：同 P1-02，排队态拒绝时文档要求返回 `"bill": null`，代码未返回。

**操作**：在排队态拒绝的响应中添加 `"bill": None`。

---

### P1-04: `/sessions/:id/stop-charging` POST 响应缺少 `electricityDetails`

**位置**：`backend/api/sessions/router.py:api_stop_charging()`

**问题**：文档要求 bill 中包含 `electricityDetails` 数组（分时段明细），但代码响应的 bill 中未包含该字段。（注意：账单记录表中已存储电费明细数据，只需在响应中返回。）

**操作**：在 stop-charging 的 bill 响应中添加 `electricityDetails` 字段，从计费引擎计算结果中提取。

---

### P2-01: 报表三个接口参数和响应需重写

#### `/admin/reports/charging-volume` GET

**位置**：`backend/service/admin/service.py:get_charging_volume_report()`

**问题**：
- 文档要求 `granularity` 参数（`day`/`week`/`month`）→ 代码未实现
- 文档要求 `dataPoints[]` → 代码返回 `byStation[]` 结构完全不同
- 文档要求顶层 `totalEnergyKwh`、`totalSessions` → 代码嵌套在 `summary` 下

**操作**：按文档要求重写报告逻辑，支持按 `granularity` 聚合的 `dataPoints[]` 数据。

#### `/admin/reports/revenue` GET

**位置**：`backend/service/admin/service.py:get_revenue_report()`

**问题**：
- 文档要求 `granularity` 参数 → 代码未实现
- 文档要求 `dataPoints[]`（含 `period`、`revenue`、`electricity`、`service`）→ 代码缺失
- 代码返回了文档未定义的 `paidSessions`

**操作**：按文档重写，添加 `granularity` 参数和 `dataPoints[]` 聚合逻辑，移除 `paidSessions`。

#### `/admin/reports/utilization` GET

**位置**：`backend/service/admin/service.py:get_utilization_report()`

**问题**：
- 文档要求 `startDate`、`endDate` 参数 → 代码未实现
- 文档要求顶层 `overallUtilization` → 代码缺失
- 文档要求 `totalChargingHours`、`totalAvailableHours` → 代码缺失（只有瞬时占用率）

**操作**：按文档重写，基于历史数据计算某时间段的利用率，而非仅返回当前瞬时值。

---

### P2-02: 未文档化的接口

| 路径 | 位置 | 操作建议 | 状态 |
|------|------|---------|------|
| `GET /api/v1/protocols` | `backend/api/protocols/router.py` | ✅ **已完成** — 已补充至 01-API接口说明.md "第一部分"之后 | 已修复 |
| `GET /api/v1/admin/queues/logs` | `backend/api/admin/queues/router.py:60-70` | ✅ **已完成** — 已补充至 01-API接口说明.md "队列管理"小节 | 已修复 |

---

## 优先级与工作量预估

| 优先级 | 编号 | 事项 | 预估工时 |
|--------|------|------|---------|
| P0 | 01, 02 | ✅ **已完成** — 配置 GET/PUT 重构、模型移除 priority、电价冲突校验、前端对齐 | 已修复 |
| P0 | 03-07 | 管理端会话、账单、队列接口对齐文档 | 待处理 |
| P1 | 01-04 | 会话接口字段修正 | 1-2 小时 |
| P2 | 01-02 | 报表重写 + 文档补充 | 4-6 小时 |

**合计**：约 8-12 小时

---

> 说明：P0 = 严重影响前后端对接，必须优先修复；P1 = 字段规范性问题，需修复但优先级低于 P0；P2 = 功能缺失或文档缺口，按迭代规划安排。
