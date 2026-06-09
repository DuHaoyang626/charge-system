# 智能充电桩调度计费系统 — API 接口说明文档

> 本文档为前端与后端之间的完整接口契约。
> 每个接口包含：请求格式、字段说明、前置条件、响应格式、字段说明、响应码、场景示例、后置操作。

---

## CHANGELOG

| 版本 | 日期       | 变更说明                         |
| ---- | ---------- | -------------------------------- |
| v1.0 | 2026-06-08 | 初版，覆盖所有用户端和管理端接口 |

---

## 通用约定

### Base URL

```
/api/v1
```

### 请求头

| Header            | 必填             | 说明                   |
| ----------------- | ---------------- | ---------------------- |
| `Content-Type`  | 是               | `application/json`   |
| `Authorization` | 是（除登录注册） | `Bearer <jwt_token>` |

### 通用响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { },
  "timestamp": 1700000000000
}
```

### 通用错误响应格式

```json
{
  "code": 400,
  "message": "具体错误描述",
  "data": null,
  "timestamp": 1700000000000
}
```

### 通用响应码

| code | 含义           | 说明                             |
| ---- | -------------- | -------------------------------- |
| 200  | 成功           | 请求正常处理                     |
| 201  | 创建成功       | POST 资源创建                    |
| 400  | 请求参数错误   | 参数校验失败、业务规则冲突       |
| 401  | 未认证         | Token 缺失或过期                 |
| 403  | 无权限         | Token 有效但无权访问             |
| 404  | 资源不存在     | 请求的资源未找到                 |
| 409  | 冲突           | 资源状态冲突（如已有进行中会话） |
| 429  | 频率限制       | 请求过于频繁                     |
| 500  | 服务器内部错误 | 未预期异常                       |

### 分页响应格式

```json
{
  "code": 200,
  "data": {
    "list": [],
    "page": 1,
    "pageSize": 20,
    "total": 100
  }
}
```

### JWT 鉴权机制

```
登录 ──→ 返回 token ──→ 后续请求携带 Authorization: Bearer <token>
                           │
                           ▼
                     Auth 中间件解码
                     claims.userId → req.userId
```

- Token 有效期：24 小时（可配置）
- 所有接口（除 `/auth/*` 外）均需携带 Token
- 管理员接口需额外校验 JWT claims 中的 `role: "admin"`

---

# 第一部分：认证模块

## POST /auth/register — 用户注册

### 功能说明

创建新的用户账号（等价于车辆注册），返回 JWT Token 使用户直接登录。

### 请求格式

```
POST /api/v1/auth/register
Content-Type: application/json
```

### 请求字段

| 字段                | 类型            | 必填 | 说明                                          |
| ------------------- | --------------- | ---- | --------------------------------------------- |
| `licensePlate`    | String          | 是   | 车牌号，唯一标识，长度 2~20，示例："京A12345" |
| `userName`        | String          | 是   | 用户昵称/车辆名称，长度 1~50                  |
| `batteryCapacity` | Number          | 是   | 电池容量（kWh），> 0，示例：60.0              |
| `password`        | String          | 是   | 密码，长度 ≥ 6                               |
| `confirmPassword` | String          | 是   | 确认密码，必须与 password 一致                |
| `protocolIds`     | Array\<Number\> | 是   | 车辆支持的充电协议 ID 列表，至少 1 个         |
| `phone`           | String          | 否   | 手机号                                        |

### 请求示例

```json
{
  "licensePlate": "京A12345",
  "userName": "我的电车",
  "batteryCapacity": 60.0,
  "password": "abc123456",
  "confirmPassword": "abc123456",
  "protocolIds": [1, 2, 3],
  "phone": "13800138000"
}
```

### 前置条件（操作契约）

| 条件 | 说明                                      |
| ---- | ----------------------------------------- |
| 前端 | 校验 password === confirmPassword         |
| 前端 | 校验 protocolIds 非空                     |
| 前端 | 校验 batteryCapacity > 0                  |
| 前端 | 校验 licensePlate 非空                    |
| 系统 | licensePlate 在数据库中唯一，不可重复注册 |

### 响应字段

| 字段             | 类型   | 始终返回 | 说明                      |
| ---------------- | ------ | -------- | ------------------------- |
| `userId`       | Number | 是       | 用户 ID                   |
| `licensePlate` | String | 是       | 车牌号                    |
| `userName`     | String | 是       | 用户名                    |
| `token`        | String | 是       | JWT Token，后续请求需携带 |

### 响应示例

```json
{
  "code": 201,
  "message": "注册成功",
  "data": {
    "userId": 1,
    "licensePlate": "京A12345",
    "userName": "我的电车",
    "token": "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOjF9.xxx"
  }
}
```

### 场景示例

#### 场景 1：正常注册

> **请求**：有效参数
> **响应**：`code: 201`，返回 token
> **前端操作**：保存 token 到本地存储，跳转到主页

#### 场景 2：车牌号已存在

> **请求**：`licensePlate: "京A12345"` 已注册
> **响应**：
>
> ```json
> { "code": 400, "message": "该车牌号已注册", "data": null }
> ```
>
> **前端操作**：提示用户"该车牌号已注册"，引导用户去登录

#### 场景 3：两次密码不一致

> **前端自行校验**，不发起请求
> **前端操作**：提示"两次密码输入不一致"，不允许提交

#### 场景 4：协议 ID 不存在

> **请求**：`protocolIds: [999]`
> **响应**：
>
> ```json
> { "code": 400, "message": "协议 ID 999 不存在", "data": null }
> ```
>
> **前端操作**：提示用户重新选择协议

### 后置操作（操作契约）

| 步骤 | 操作                                                      |
| ---- | --------------------------------------------------------- |
| 1    | 前端将 token 存入 localStorage/sessionStorage             |
| 2    | 前端将 userId, userName, licensePlate 存入本地            |
| 3    | 前端跳转到主页 `/home`                                  |
| 4    | 后续所有请求自动携带 `Authorization: Bearer <token>` 头 |

---

## POST /auth/login — 用户登录

### 功能说明

用户使用车牌号和密码登录，获取 JWT Token。

### 请求格式

```
POST /api/v1/auth/login
Content-Type: application/json
```

### 请求字段

| 字段             | 类型   | 必填 | 说明   |
| ---------------- | ------ | ---- | ------ |
| `licensePlate` | String | 是   | 车牌号 |
| `password`     | String | 是   | 密码   |

### 请求示例

```json
{
  "licensePlate": "京A12345",
  "password": "abc123456"
}
```

### 前置条件（操作契约）

| 条件 | 说明                                |
| ---- | ----------------------------------- |
| 前端 | 校验 licensePlate 和 password 非空  |
| 系统 | 无（不限制登录频率，除 429 限流外） |

### 响应字段

| 字段             | 类型   | 始终返回 | 说明                                              |
| ---------------- | ------ | -------- | ------------------------------------------------- |
| `userId`       | Number | 是       | 用户 ID                                           |
| `licensePlate` | String | 是       | 车牌号                                            |
| `userName`     | String | 是       | 用户名                                            |
| `token`        | String | 是       | JWT Token                                         |
| `role`         | String | 是       | 用户角色，普通用户为 `user`，管理员为 `admin` |

### 响应示例

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "userId": 1,
    "licensePlate": "京A12345",
    "token": "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOjF9.xxx",
    "userName": "我的电车",
    "role": "user"
  }
}
```

### 场景示例

#### 场景 1：正常登录

> **响应**：`code: 200`，返回 token 和用户基础身份信息
> **前端操作**：保存 token，设置请求拦截器，跳转到主页 `/home`

#### 场景 2：密码错误

> **响应**：
>
> ```json
> { "code": 400, "message": "账号或密码错误", "data": null }
> ```
>
> **前端操作**：提示"账号或密码错误"，不清空密码框，允许用户重新输入
> **注意**：不要提示"账号不存在"或"密码错误"这种具体信息，防撞库

#### 场景 3：账号不存在

> **响应**：
>
> ```json
> { "code": 400, "message": "账号或密码错误", "data": null }
> ```
>
> **前端操作**：同上，提示"账号或密码错误"，同时提供"去注册"链接

### 后置操作（操作契约）

| 步骤 | 操作                                                      |
| ---- | --------------------------------------------------------- |
| 1    | 前端将 token 存入 localStorage/sessionStorage             |
| 2    | 前端设置 axios 拦截器，自动在请求头中携带 token           |
| 3    | 前端跳转到主页 `/home`                                  |
| 4    | `/home` 页面加载后调用 `GET /users/me` 初始化用户状态 |

---

## GET /users/me — 获取当前用户信息

### 功能说明

获取当前登录用户的车辆信息、支持协议和活动会话状态。主页加载、页面刷新或应用初始化时调用本接口恢复用户端业务状态。本接口不承担页面跳转职责。

### 请求格式

```
GET /api/v1/users/me
Authorization: Bearer <token>
```

### 前置条件（操作契约）

| 条件 | 说明                       |
| ---- | -------------------------- |
| 前端 | 必须已登录，携带有效 token |
| 系统 | Token 对应用户存在         |

### 响应字段

| 字段                          | 类型         | 始终返回 | 说明                                    |
| ----------------------------- | ------------ | -------- | --------------------------------------- |
| `userId`                    | Number       | 是       | 用户 ID                                 |
| `licensePlate`              | String       | 是       | 车牌号                                  |
| `userName`                  | String       | 是       | 用户名                                  |
| `phone`                     | String\|null | 是       | 手机号                                  |
| `batteryCapacity`           | Number       | 是       | 电池容量（kWh）                         |
| `protocols`                 | Array        | 是       | 用户支持的协议列表                      |
| `protocols[].id`            | Number       | 是       | 协议 ID                                 |
| `protocols[].name`          | String       | 是       | 协议名称                                |
| `protocols[].powerKw`       | Number       | 是       | 功率（kW）                              |
| `activeSession`             | Object\|null | 是       | 当前进行中的会话，null 表示无           |
| `activeSession.sessionId`   | Number       | 否       | 会话 ID                                 |
| `activeSession.status`      | String       | 否       | `queued` / `waiting` / `charging` |
| `activeSession.stationName` | String       | 否       | 当前充电桩名称                          |
| `activeSession.progress`    | Number       | 否       | 充电进度百分比                          |

### 响应示例

```json
{
  "code": 200,
  "data": {
    "userId": 1,
    "licensePlate": "京A12345",
    "userName": "我的电车",
    "phone": "13800138000",
    "batteryCapacity": 60.0,
    "protocols": [
      {"id": 1, "name": "AC 7kW", "powerKw": 7.0},
      {"id": 3, "name": "DC 120kW", "powerKw": 120.0}
    ],
    "activeSession": {
      "sessionId": 101,
      "status": "charging",
      "stationName": "A区-01号桩",
      "progress": 55
    }
  }
}
```

### 场景示例

#### 场景 1：无进行中会话

> **响应**：`activeSession: null`
> **前端操作**：`/home` 页面展示发起充电入口

#### 场景 2：存在进行中会话

> **响应**：`activeSession.status` 为 `queued`、`waiting` 或 `charging`
> **前端操作**：`/home` 页面展示当前会话入口，用户点击后进入会话详情页

### 后置操作（操作契约）

| 步骤 | 操作                                                                  |
| ---- | --------------------------------------------------------------------- |
| 1    | 前端缓存 userId, userName, licensePlate, batteryCapacity 和 protocols |
| 2    | 前端在 `/home` 内根据 activeSession 渲染发起充电入口或当前会话入口  |
| 3    | 用户点击当前会话入口后，前端跳转到会话详情页                          |

---

# 第二部分：充电桩模块（用户端）

## GET /stations — 获取所有充电桩状态

### 功能说明

获取所有充电桩的概要信息，包括状态、各区域容量和当前数量、支持的协议、预估等待时长。主页完成用户状态初始化后调用此接口，展示各桩概览。

### 请求格式

```
GET /api/v1/stations
Authorization: Bearer <token>
```

### 前置条件（操作契约）

| 条件 | 说明                       |
| ---- | -------------------------- |
| 前端 | 必须已登录，携带有效 token |
| 系统 | 无                         |

### 响应字段

| 字段                                        | 类型   | 始终返回 | 说明                                                                           |
| ------------------------------------------- | ------ | -------- | ------------------------------------------------------------------------------ |
| `stations`                                | Array  | 是       | 充电桩列表                                                                     |
| `stations[].id`                           | Number | 是       | 充电桩 ID                                                                      |
| `stations[].name`                         | String | 是       | 充电桩名称/编号                                                                |
| `stations[].status`                       | String | 是       | `running` 运行中 / `stopping` 停止中 / `stopped` 已停止 / `error` 异常 |
| `stations[].queueCount`                   | Number | 是       | 当前排队区车辆数                                                               |
| `stations[].waitingCount`                 | Number | 是       | 当前等待区车辆数                                                               |
| `stations[].chargingCount`                | Number | 是       | 当前充电区车辆数                                                               |
| `stations[].queueCapacity`                | Number | 是       | 排队区总容量                                                                   |
| `stations[].waitingCapacity`              | Number | 是       | 等待区总容量                                                                   |
| `stations[].chargingCapacity`             | Number | 是       | 充电区总容量                                                                   |
| `stations[].supportedProtocols`           | Array  | 是       | 支持的充电协议列表                                                             |
| `stations[].supportedProtocols[].id`      | Number | 是       | 协议 ID                                                                        |
| `stations[].supportedProtocols[].name`    | String | 是       | 协议名称                                                                       |
| `stations[].supportedProtocols[].powerKw` | Number | 是       | 功率（kW）                                                                     |
| `stations[].estimatedWaitMinutes`         | Number | 是       | 预估等待时长（分钟），基于当前队列深度和历史平均充电时长估算                   |

### 响应示例

```json
{
  "code": 200,
  "data": {
    "stations": [
      {
        "id": 1,
        "name": "A区-01号桩",
        "status": "running",
        "queueCount": 3,
        "waitingCount": 2,
        "chargingCount": 1,
        "queueCapacity": 10,
        "waitingCapacity": 5,
        "chargingCapacity": 4,
        "supportedProtocols": [
          {"id": 1, "name": "AC 7kW", "powerKw": 7.0},
          {"id": 3, "name": "DC 120kW", "powerKw": 120.0}
        ],
        "estimatedWaitMinutes": 15
      },
      {
        "id": 2,
        "name": "B区-02号桩",
        "status": "stopping",
        "queueCount": 0,
        "waitingCount": 2,
        "chargingCount": 2,
        "queueCapacity": 10,
        "waitingCapacity": 5,
        "chargingCapacity": 4,
        "supportedProtocols": [
          {"id": 1, "name": "AC 7kW", "powerKw": 7.0}
        ],
        "estimatedWaitMinutes": 20
      }
    ]
  }
}
```

### 场景示例

#### 场景 1：正常展示所有桩

> **前端操作**：列表展示所有充电桩，每个桩显示：
>
> - 名称 + 状态标签（running 绿色 / stopping 黄色 / stopped 灰色 / error 红色）
> - 各区域占位条（例如：排队 3/10，等待 2/5，充电 1/4）
> - 预估等待时间
> - 支持的协议图标列表
> - 发起充电按钮（仅在 running 状态可点击）

#### 场景 2：所有桩都已满（queueCount = queueCapacity）

> **前端操作**：所有桩的"发起充电"按钮置灰，显示"当前所有充电桩已满，请稍后再试"
> **用户理解**：没有可用的排队位置，当前无法发起充电

#### 场景 3：某桩处于 error 状态

> **前端操作**：显示红色"异常"标签，不显示"发起充电"按钮，可显示"维修中"说明
> **用户理解**：该桩不可用

#### 场景 4：用户已有一个进行中的会话

> **注意**：主页初始化时通过 `GET /users/me` 的 `activeSession` 提示当前会话；本场景用于处理并发或状态过期情况：
> **系统表现**：`POST /sessions` 返回 `code: 409`
> **前端操作**：跳转到进行中的充电进度页

### 后置操作（操作契约）

| 步骤 | 操作                                                                                                                                      |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | 前端将桩列表渲染到页面                                                                                                                    |
| 2    | 用户选择一个 running 的桩，点击"发起充电"                                                                                                 |
| 3    | 跳转到充电参数设置页（选择电量、协议）                                                                                                    |
| 4    | **注意**：`POST /sessions` 不传 stationId，由系统自动分配最优桩。前端展示桩列表仅用于用户参考，不代表用户选择的桩就是最终分配的桩 |

> **设计决策**：为什么前端展示桩列表但 POST /sessions 不传 stationId？
> 当前设计由 DispatchService 根据系统算法自动分配最优桩。`POST /sessions` 不接收 stationId，前端展示的桩列表仅作为用户了解排队情况的参考信息。

---

## GET /stations/:id — 充电桩详情

### 功能说明

获取单个充电桩的详细信息，包括三个区域的完整队列列表。用户点击某个桩时调用，查看具体排队情况。

### 请求格式

```
GET /api/v1/stations/:id
Authorization: Bearer <token>
```

| 参数   | 位置 | 类型   | 必填 | 说明      |
| ------ | ---- | ------ | ---- | --------- |
| `id` | Path | Number | 是   | 充电桩 ID |

### 前置条件（操作契约）

| 条件 | 说明           |
| ---- | -------------- |
| 前端 | 必须已登录     |
| 系统 | 充电桩 ID 存在 |

### 响应字段

| 字段                                 | 类型   | 始终返回 | 说明                               |
| ------------------------------------ | ------ | -------- | ---------------------------------- |
| `id`                               | Number | 是       | 充电桩 ID                          |
| `name`                             | String | 是       | 充电桩名称                         |
| `status`                           | String | 是       | 运行状态                           |
| `queueCapacity`                    | Number | 是       | 排队区容量                         |
| `waitingCapacity`                  | Number | 是       | 等待区容量                         |
| `chargingCapacity`                 | Number | 是       | 充电区容量                         |
| `queueCount`                       | Number | 是       | 当前排队数                         |
| `waitingCount`                     | Number | 是       | 当前等待数                         |
| `chargingCount`                    | Number | 是       | 当前充电数                         |
| `queueList`                        | Array  | 是       | 排队区车辆列表                     |
| `queueList[].sessionId`            | Number | -        | 会话 ID                            |
| `queueList[].licensePlate`         | String | -        | 车牌号（脱敏处理？可配置）         |
| `queueList[].position`             | Number | -        | 在队列中的位置（从 1 开始）        |
| `queueList[].requestedEnergyKwh`   | Number | -        | 目标充电量                         |
| `queueList[].supportedProtocols`   | Array  | -        | 该车辆支持的协议                   |
| `queueList[].status`               | String | -        | `queued`                         |
| `queueList[].estimatedWaitMinutes` | Number | -        | 预估等待进入等待区的时间           |
| `waitingList`                      | Array  | 是       | 等待区车辆列表（字段同 queueList） |
| `chargingList`                     | Array  | 是       | 充电区车辆列表                     |
| `chargingList[].sessionId`         | Number | -        | 会话 ID                            |
| `chargingList[].licensePlate`      | String | -        | 车牌号                             |
| `chargingList[].position`          | Number | -        | 充电位编号                         |
| `chargingList[].chargedEnergyKwh`  | Number | -        | 已充电量                           |
| `chargingList[].targetEnergyKwh`   | Number | -        | 目标电量                           |
| `chargingList[].protocol`          | Object | -        | 当前使用的充电协议                 |
| `chargingList[].progress`          | Number | -        | 充电进度百分比（0-100）            |
| `chargingList[].estimatedEndTime`  | String | -        | 预计结束时间（ISO 8601）           |
| `supportedProtocols`               | Array  | 是       | 该桩支持的所有协议                 |

### 响应示例

```json
{
  "code": 200,
  "data": {
    "id": 1,
    "name": "A区-01号桩",
    "status": "running",
    "queueCapacity": 10,
    "waitingCapacity": 5,
    "chargingCapacity": 4,
    "queueCount": 3,
    "waitingCount": 2,
    "chargingCount": 1,
    "queueList": [
      {
        "sessionId": 101,
        "licensePlate": "京A12345",
        "position": 1,
        "requestedEnergyKwh": 50.0,
        "supportedProtocols": [{"id":1,"name":"AC 7kW","powerKw":7.0}],
        "status": "queued",
        "estimatedWaitMinutes": 5
      }
    ],
    "waitingList": [
      {
        "sessionId": 100,
        "licensePlate": "京C99999",
        "position": 1,
        "requestedEnergyKwh": 40.0,
        "supportedProtocols": [
          {"id":1,"name":"AC 7kW","powerKw":7.0},
          {"id":3,"name":"DC 120kW","powerKw":120.0}
        ],
        "status": "waiting",
        "estimatedWaitMinutes": 10
      }
    ],
    "chargingList": [
      {
        "sessionId": 99,
        "licensePlate": "京B67890",
        "position": 1,
        "chargedEnergyKwh": 20.5,
        "targetEnergyKwh": 60.0,
        "protocol": {"id":3,"name":"DC 120kW","powerKw":120.0},
        "progress": 34,
        "estimatedEndTime": "2026-06-08T14:30:00"
      }
    ],
    "supportedProtocols": [
      {"id":1,"name":"AC 7kW","powerKw":7.0},
      {"id":3,"name":"DC 120kW","powerKw":120.0}
    ]
  }
}
```

### 场景示例

#### 场景 1：桩正常运行，各区域有车辆

> **前端操作**：
>
> - Tab 或分区展示三个区域的车辆列表
> - 排队区显示每辆车的排队位置和预估时间
> - 充电区显示进度条、当前协议和预估完成时间

#### 场景 2：桩 ID 不存在

> **响应**：
>
> ```json
> { "code": 404, "message": "充电桩不存在", "data": null }
> ```
>
> **前端操作**：提示"充电桩不存在"，返回列表页

#### 场景 3：用户查看自己的排队位置

> **前端操作**：在 queueList 中找到自己 sessionId 对应的项，高亮显示"我的位置"

### 后置操作（操作契约）

| 步骤 | 操作                                         |
| ---- | -------------------------------------------- |
| 1    | 前端渲染排队、等待、充电三个区域的列表       |
| 2    | 用户查看整体排队情况，决定是否发起充电或换队 |

---

# 第三部分：充电会话模块

## POST /sessions — 发起充电请求

### 功能说明

用户发起充电请求，系统自动分配最佳充电桩并将车辆加入排队区。

### 请求格式

```
POST /api/v1/sessions
Authorization: Bearer <token>
Content-Type: application/json
```

### 请求字段

| 字段                   | 类型            | 必填 | 说明                                                            |
| ---------------------- | --------------- | ---- | --------------------------------------------------------------- |
| `requestedEnergyKwh` | Number          | 是   | 目标充电量（kWh），> 0，示例：60.0                              |
| `protocolIds`        | Array\<Number\> | 是   | 本次充电支持的协议 ID 列表，至少 1 个，必须在用户注册协议范围内 |

### 请求示例

```json
{
  "requestedEnergyKwh": 60.0,
  "protocolIds": [1, 2, 3]
}
```

> **注意**：请求体中**不包含** `stationId`、`userId`、`licensePlate`。
>
> - `stationId`：由系统 DispatchService 自动计算最优桩
> - `userId`：从 JWT Token 中提取
> - `licensePlate`：从用户信息关联

### 前置条件（操作契约）

| 条件 | 说明                                                            |
| ---- | --------------------------------------------------------------- |
| 前端 | 校验 `requestedEnergyKwh > 0`                                 |
| 前端 | 校验 `protocolIds` 非空且均在用户支持的范围内                 |
| 前端 | 检查登录状态，未登录不可发起                                    |
| 系统 | 至少有一个 `running` 状态的充电桩且有可用排队位               |
| 系统 | 该用户没有进行中的会话（status ∈ {queued, waiting, charging}） |
| 系统 | 所有 `protocolIds` 必须在该用户注册时登记的协议范围内         |

### 响应字段

| 字段                     | 类型   | 始终返回 | 说明                                  |
| ------------------------ | ------ | -------- | ------------------------------------- |
| `sessionId`            | Number | 是       | 会话 ID，后续所有操作均基于此 ID      |
| `status`               | String | 是       | `queued` — 创建成功后始终为 queued |
| `zone`                 | String | 是       | `queue` — 当前所在区域             |
| `queuePosition`        | Number | 是       | 排队区中的位置（从 1 开始）           |
| `station`              | Object | 是       | 分配的充电桩                          |
| `station.id`           | Number | 是       | 充电桩 ID                             |
| `station.name`         | String | 是       | 充电桩名称                            |
| `requestedEnergyKwh`   | Number | 是       | 目标充电量                            |
| `estimatedWaitMinutes` | Number | 是       | 预估等待进入等待区的时间（分钟）      |
| `createdAt`            | String | 是       | 创建时间（ISO 8601）                  |

### 响应示例

```json
{
  "code": 201,
  "message": "充电请求已提交，进入排队区",
  "data": {
    "sessionId": 101,
    "status": "queued",
    "zone": "queue",
    "queuePosition": 3,
    "station": {"id": 1, "name": "A区-01号桩"},
    "requestedEnergyKwh": 60.0,
    "estimatedWaitMinutes": 15,
    "createdAt": "2026-06-08T14:00:00"
  }
}
```

### 场景示例

#### 场景 1：正常发起成功

> **响应**：`code: 201`，返回排队位置
> **前端操作**：
>
> 1. 跳转到排队进度页
> 2. 显示"已进入 A区-01号桩 排队区，当前位置：第 3 位"
> 3. 显示预估等待时间 15 分钟
> 4. 开始轮询 `GET /sessions/:id`（每 3~5 秒）
> 5. 提供"换队"和"取消"按钮

#### 场景 2：所有充电桩已满

> **响应**：
>
> ```json
> { "code": 400, "message": "当前所有充电桩排队区已满，请稍后再试", "data": null }
> ```
>
> **前端操作**：弹窗提示"当前所有充电桩排队区已满"，不关闭当前页面，用户可稍后重试

#### 场景 3：用户已有进行中的会话

> **响应**：
>
> ```json
> { "code": 409, "message": "您已有进行中的充电会话，请先完成或取消", "data": { "activeSessionId": 99 } }
> ```
>
> **前端操作**：弹窗提示"您已有进行中的充电"，点击确定跳转到该会话的进度页

#### 场景 4：token 过期/无效

> **响应**：
>
> ```json
> { "code": 401, "message": "Token 已过期，请重新登录", "data": null }
> ```
>
> **前端操作**：清除本地 token，跳转到登录页

### 后置操作（操作契约）

| 步骤 | 操作                                          |
| ---- | --------------------------------------------- |
| 1    | 前端跳转到排队进度页                          |
| 2    | 启动 `GET /sessions/:id` 轮询（3~5 秒间隔） |
| 3    | 渲染当前状态：排队位置、站名、预估时间        |
| 4    | 提供"换队"和"取消"操作入口                    |

---

## GET /sessions/:id — 获取会话详情

### 功能说明

获取单个充电会话的完整信息。用于页面整页刷新后恢复状态，或用户主动查看完整详情。

### 请求格式

```
GET /api/v1/sessions/:id
Authorization: Bearer <token>
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 会话 ID |

### 前置条件（操作契约）

| 条件 | 说明                         |
| ---- | ---------------------------- |
| 前端 | 必须已登录，携带有效 token   |
| 系统 | 会话 ID 存在，且属于当前用户 |

### 响应字段

| 字段                              | 类型         | 始终返回 | 条件说明                                                                |
| --------------------------------- | ------------ | -------- | ----------------------------------------------------------------------- |
| `id`                            | Number       | 是       | 会话 ID                                                                 |
| `status`                        | String       | 是       | `queued` / `waiting` / `charging` / `completed` / `cancelled` |
| `zone`                          | String       | 是       | `queue` / `waiting` / `charging` / `null`（完成后）             |
| `station`                       | Object       | 是       | 当前所在/处理充电桩                                                     |
| `station.id`                    | Number       | 是       | 桩 ID                                                                   |
| `station.name`                  | String       | 是       | 桩名称                                                                  |
| `protocol`                      | Object\|null | 状态相关 | 充电态时返回当前协议，排队/等待态为 null                                |
| `protocol.id`                   | Number       | -        | 协议 ID                                                                 |
| `protocol.name`                 | String       | -        | 协议名称                                                                |
| `protocol.powerKw`              | Number       | -        | 功率                                                                    |
| `requestedEnergyKwh`            | Number       | 是       | 目标充电量                                                              |
| `chargedEnergyKwh`              | Number       | 是       | 已充电量（排队/等待态为 0）                                             |
| `progress`                      | Number       | 是       | 充电进度百分比（排队态 0，充电态 0~100）                                |
| `chargingDuration`              | String       | 充电态   | 已充电时长，格式 `HH:mm:ss`                                           |
| `queuePosition`                 | Number\|null | 状态相关 | 排队/等待态返回位置编号，充电态为 null                                  |
| `supportedProtocols`            | Array        | 是       | 用户本次选择的协议列表                                                  |
| `enteredQueueAt`                | String\|null | 是       | 进入排队区时间（ISO 8601）                                              |
| `enteredWaitingAt`              | String\|null | 是       | 进入等待区时间                                                          |
| `startedChargingAt`             | String\|null | 是       | 开始充电时间                                                            |
| `completedAt`                   | String\|null | 是       | 结束充电时间                                                            |
| `estimatedEndTime`              | String\|null | 充电态   | 预计结束时间                                                            |
| `currentFee`                    | Object       | 是       | **实时费用，所有状态均携带**                                      |
| `currentFee.electricityFee`     | Number       | 是       | 电费（排队/等待态为 0）                                                 |
| `currentFee.electricityDetails` | Array        | 充电态   | 各时段电量电价明细                                                      |
| `currentFee.baseServiceFee`     | Number       | 是       | 基础服务费（进入等待区后为 5.00）                                       |
| `currentFee.timeServiceFee`     | Number       | 是       | 时长服务费（充电态累积）                                                |
| `currentFee.totalServiceFee`    | Number       | 是       | 服务费合计                                                              |
| `currentFee.totalFee`           | Number       | 是       | 总费用                                                                  |
| `bill`                          | Object\|null | 完成后   | 已完成/已取消时返回账单摘要                                             |

### 各状态响应示例

#### 排队中 (queued)

```json
{
  "code": 200,
  "data": {
    "id": 101,
    "status": "queued",
    "zone": "queue",
    "station": {"id": 1, "name": "A区-01号桩"},
    "protocol": null,
    "requestedEnergyKwh": 60.0,
    "chargedEnergyKwh": 0,
    "progress": 0,
    "chargingDuration": null,
    "queuePosition": 3,
    "supportedProtocols": [{"id":1,"name":"AC 7kW"}, {"id":3,"name":"DC 120kW"}],
    "enteredQueueAt": "2026-06-08T14:00:00",
    "enteredWaitingAt": null,
    "startedChargingAt": null,
    "completedAt": null,
    "estimatedEndTime": null,
    "currentFee": {
      "electricityFee": 0,
      "electricityDetails": [],
      "baseServiceFee": 0,
      "timeServiceFee": 0,
      "totalServiceFee": 0,
      "totalFee": 0
    },
    "bill": null
  }
}
```

#### 等待中 (waiting)

```json
{
  "code": 200,
  "data": {
    "id": 101,
    "status": "waiting",
    "zone": "waiting",
    "station": {"id": 1, "name": "A区-01号桩"},
    "protocol": null,
    "requestedEnergyKwh": 60.0,
    "chargedEnergyKwh": 0,
    "progress": 0,
    "chargingDuration": null,
    "queuePosition": 1,
    "supportedProtocols": [{"id":1,"name":"AC 7kW"}, {"id":3,"name":"DC 120kW"}],
    "enteredQueueAt": "2026-06-08T14:00:00",
    "enteredWaitingAt": "2026-06-08T14:15:00",
    "startedChargingAt": null,
    "completedAt": null,
    "estimatedEndTime": null,
    "currentFee": {
      "electricityFee": 0,
      "electricityDetails": [],
      "baseServiceFee": 5.00,
      "timeServiceFee": 0,
      "totalServiceFee": 5.00,
      "totalFee": 5.00
    },
    "bill": null
  }
}
```

#### 充电中 (charging)

```json
{
  "code": 200,
  "data": {
    "id": 101,
    "status": "charging",
    "zone": "charging",
    "station": {"id": 1, "name": "A区-01号桩"},
    "protocol": {"id": 3, "name": "DC 120kW", "powerKw": 120.0},
    "requestedEnergyKwh": 60.0,
    "chargedEnergyKwh": 25.3,
    "progress": 42,
    "chargingDuration": "00:12:30",
    "queuePosition": null,
    "supportedProtocols": [{"id":1,"name":"AC 7kW"}, {"id":3,"name":"DC 120kW"}],
    "enteredQueueAt": "2026-06-08T14:00:00",
    "enteredWaitingAt": "2026-06-08T14:02:00",
    "startedChargingAt": "2026-06-08T14:05:00",
    "completedAt": null,
    "estimatedEndTime": "2026-06-08T14:35:00",
    "currentFee": {
      "electricityFee": 20.24,
      "electricityDetails": [
        {"period": "平时", "energy": 25.3, "price": 0.8, "fee": 20.24}
      ],
      "baseServiceFee": 5.00,
      "timeServiceFee": 1.88,
      "totalServiceFee": 6.88,
      "totalFee": 27.12
    },
    "bill": null
  }
}
```

#### 已完成 (completed)

```json
{
  "code": 200,
  "data": {
    "id": 101,
    "status": "completed",
    "zone": null,
    "station": {"id": 1, "name": "A区-01号桩"},
    "protocol": {"id": 3, "name": "DC 120kW", "powerKw": 120.0},
    "requestedEnergyKwh": 60.0,
    "chargedEnergyKwh": 60.0,
    "progress": 100,
    "chargingDuration": "00:30:00",
    "queuePosition": null,
    "supportedProtocols": [{"id":1,"name":"AC 7kW"}, {"id":3,"name":"DC 120kW"}],
    "enteredQueueAt": "2026-06-08T14:00:00",
    "enteredWaitingAt": "2026-06-08T14:02:00",
    "startedChargingAt": "2026-06-08T14:05:00",
    "completedAt": "2026-06-08T14:35:00",
    "estimatedEndTime": null,
    "currentFee": {
      "electricityFee": 36.16,
      "electricityDetails": [
        {"period": "平时", "energy": 45.2, "price": 0.8, "fee": 36.16}
      ],
      "baseServiceFee": 5.00,
      "timeServiceFee": 4.50,
      "totalServiceFee": 9.50,
      "totalFee": 45.66
    },
    "bill": {
      "billId": 1,
      "totalFee": 45.66,
      "paymentStatus": "unpaid"
    }
  }
}
```

#### 已取消 (cancelled) — 等待区取消

```json
{
  "code": 200,
  "data": {
    "id": 101,
    "status": "cancelled",
    "zone": null,
    "station": {"id": 1, "name": "A区-01号桩"},
    "protocol": null,
    "requestedEnergyKwh": 60.0,
    "chargedEnergyKwh": 0,
    "progress": 0,
    "chargingDuration": null,
    "queuePosition": null,
    "supportedProtocols": [...],
    "enteredQueueAt": "2026-06-08T14:00:00",
    "enteredWaitingAt": "2026-06-08T14:15:00",
    "startedChargingAt": null,
    "completedAt": "2026-06-08T14:16:00",
    "estimatedEndTime": null,
    "currentFee": {
      "electricityFee": 0,
      "electricityDetails": [],
      "baseServiceFee": 5.00,
      "timeServiceFee": 0,
      "totalServiceFee": 5.00,
      "totalFee": 5.00
    },
    "bill": {
      "billId": 2,
      "totalFee": 5.00,
      "paymentStatus": "unpaid"
    }
  }
}
```

### 轮询生命周期完整时序

```
POST /sessions 创建会话
  │
  ▼
GET /sessions/:id 每 3~5 秒轮询
  │
  ├── queued：更新排队位置、预估等待时间
  │
  ├── waiting：更新等待位置、基础服务费状态，展示确认/取消入口
  │
  ├── charging：更新已充电量、进度、已充电时长、实时费用
  │
  ├── completed：停止轮询，读取 bill.billId，调用 GET /bills/:id
  │
  └── cancelled：停止轮询；存在账单时调用 GET /bills/:id
```

### 后端自动结束充电 → 前端收到通知的完整链路

```
后端 MonitorService 定时检测
  │
  ├─ 轮询 DB 中所有 charging 状态的会话
  │
  ├─ 检测到 session 101: chargedEnergy=60.0 >= requestedEnergy=60.0
  │
  ├─ 执行 StopCharging()
  │    ├─ 停止物理充电
  │    ├─ 记录 completed_at = now
  │    └─ 更新 status = "completed"
  │
  ├─ 执行 BillingService.calculateFee(sessionId)
  │    ├─ 查询充电时段电价
  │    ├─ 查询服务费阶梯
  │    └─ 生成 bill 记录 → billId = 1
  │
  ├─ 写入 DB: session.status = "completed", billId 关联
  │
  └─ 等待前端下一次轮询 ──► 前端 GET /sessions/:id/progress
                                      │
                                      ▼
                               status: "completed"
                               billId: 1
                               currentFee.totalFee: 45.66
                                      │
                                      ▼
                              前端：停止轮询 → 展示金额 → 跳转支付
```

### 场景示例

#### 场景 1：用户刷新页面后恢复状态

> **用户操作**：在充电进行中刷新页面
> **前端操作**：
>
> 1. 从本地存储读取 sessionId
> 2. 调用 `GET /sessions/:id` 获取完整状态
> 3. 根据 `status` 渲染对应页面（排队进度条/充电进度页/账单页）
> 4. 若 `status` 为 `queued`、`waiting` 或 `charging`，继续以 3~5 秒间隔轮询本接口
> 5. 若 `status` 为 `completed` 或 `cancelled`，停止轮询并调用 `GET /bills/:id`

#### 场景 2：正常轮询直到充电结束

> **前置**：会话已进入 `charging` 状态
> **过程**：
>
> - T=0：`status: "charging", progress: 0, currentFee.totalFee: 0`
> - T=3：`status: "charging", progress: 5, currentFee.totalFee: 3.20`
> - T=6：`status: "charging", progress: 10, currentFee.totalFee: 6.40`
> - T=180：`status: "completed", progress: 100, bill.billId: 1`
>   **前端操作**：第 180 秒收到 `completed` 后停止轮询，调用 `GET /bills/1` 获取完整账单详情

#### 场景 3：用户手动停止充电

> **前端操作**：用户点击"停止充电"后调用 `POST /sessions/:id/stop-charging`
> **系统响应**：返回 `status: "completed"` 和 `bill`
> **前端操作**：停止轮询，调用 `GET /bills/:id` 获取完整账单详情

#### 场景 4：用户主动取消

> **前端操作**：用户在排队区或等待区点击"取消"后调用 `POST /sessions/:id/cancel`
> **系统响应**：返回 `status: "cancelled"`；等待区取消时返回 `bill`
> **前端操作**：停止轮询；存在 billId 时调用 `GET /bills/:id` 获取账单详情

#### 场景 5：查看不属于自己的会话

> **响应**：
>
> ```json
> { "code": 403, "message": "无权访问该会话", "data": null }
> ```
>
> **前端操作**：停止轮询，提示"无权访问"，返回主页

#### 场景 6：轮询时网络断开

> **前端操作**：检测到网络错误后显示"网络连接断开"，按 1s、2s、4s、8s、30s 上限重试；网络恢复后继续调用 `GET /sessions/:id` 获取最新状态。

### 前端代码逻辑伪代码

```javascript
const sessionId = response.data.sessionId;

const pollingInterval = setInterval(async () => {
  try {
    const res = await api.get(`/sessions/${sessionId}`);
    const data = res.data.data;

    updateUI(data);

    if (data.status === 'completed' || data.status === 'cancelled') {
      clearInterval(pollingInterval);
      if (data.bill?.billId) {
        navigateToBill(data.bill.billId);
      } else {
        navigateToHome();
      }
    }
  } catch (err) {
    if (err.code === 403 || err.code === 404) {
      clearInterval(pollingInterval);
      navigateToHome();
    }
  }
}, 3000);

onUnmount(() => clearInterval(pollingInterval));
```

### 后置操作（操作契约）

| 状态          | 操作                                                    |
| ------------- | ------------------------------------------------------- |
| `queued`    | 更新排队位置和预估时间，保持轮询                        |
| `waiting`   | 更新等待位置，展示基础服务费和确认/取消入口，保持轮询   |
| `charging`  | 更新进度条、时长和实时金额，保持轮询                    |
| `completed` | 停止轮询，读取 `bill.billId`，调用 `GET /bills/:id` |
| `cancelled` | 停止轮询；存在账单时调用 `GET /bills/:id`             |

---

## PUT /sessions/:id/energy — 修改目标电量

### 功能说明

修改充电会话的目标电量。排队/等待态可随意修改；充电态修改时新值必须大于已充电量。

### 请求格式

```
PUT /api/v1/sessions/:id/energy
Authorization: Bearer <token>
Content-Type: application/json
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 会话 ID |

### 请求字段

| 字段                   | 类型   | 必填 | 说明                                                                    |
| ---------------------- | ------ | ---- | ----------------------------------------------------------------------- |
| `requestedEnergyKwh` | Number | 是   | 新目标电量（kWh），排队/等待态任意值 > 0，充电态必须 > chargedEnergyKwh |

### 请求示例

```json
{
  "requestedEnergyKwh": 80.0
}
```

### 前置条件（操作契约）

| 条件 | 说明                                                                                               |
| ---- | -------------------------------------------------------------------------------------------------- |
| 前端 | `queued` / `waiting` 态：校验 `requestedEnergyKwh > 0`                                       |
| 前端 | `charging` 态：校验 `requestedEnergyKwh > chargedEnergyKwh`（前端需缓存当前 chargedEnergyKwh） |
| 前端 | 展示上限参考值：不超过电池容量（来自 `GET /users/me` 的 `batteryCapacity`）                    |
| 系统 | 会话存在且属于当前用户                                                                             |
| 系统 | 会话状态为 {queued, waiting, charging}（不可修改已完成/已取消的）                                  |

### 响应字段

| 字段                    | 类型         | 始终返回 | 说明                                                                      |
| ----------------------- | ------------ | -------- | ------------------------------------------------------------------------- |
| `sessionId`           | Number       | 是       | 会话 ID                                                                   |
| `requestedEnergyKwh`  | Number       | 是       | 更新后的目标电量                                                          |
| `chargedEnergyKwh`    | Number       | 是       | 当前已充电量                                                              |
| `protocol`            | Object\|null | 充电态   | 当前使用协议                                                              |
| `chargingDuration`    | String\|null | 充电态   | 已充电时长                                                                |
| `currentFee`          | Object       | 是       | **实时费用快照**（与 `GET /sessions/:id` 中 currentFee 结构相同） |
| `currentFee.totalFee` | Number       | 是       | 截至此刻的总费用                                                          |
| `estimatedEndTime`    | String\|null | 充电态   | 基于新电量重新估算的结束时间                                              |
| `estimatedTotalFee`   | Number\|null | 充电态   | 基于新电量估算的**最终总费用**                                      |

### 响应示例

```json
{
  "code": 200,
  "message": "目标电量已更新",
  "data": {
    "sessionId": 101,
    "requestedEnergyKwh": 80.0,
    "chargedEnergyKwh": 25.3,
    "protocol": {"id": 3, "name": "DC 120kW", "powerKw": 120.0},
    "chargingDuration": "00:12:30",
    "currentFee": {
      "electricityFee": 20.24,
      "electricityDetails": [
        {"period": "平时", "energy": 25.3, "price": 0.8, "fee": 20.24}
      ],
      "baseServiceFee": 5.00,
      "timeServiceFee": 1.88,
      "totalServiceFee": 6.88,
      "totalFee": 27.12
    },
    "estimatedEndTime": "2026-06-08T14:50:00",
    "estimatedTotalFee": 77.32
  }
}
```

### 场景示例

#### 场景 1：充电中调高电量（正常场景）

> **前置状态**：`chargedEnergyKwh: 25.3, requestedEnergyKwh: 60.0`
> **请求**：`requestedEnergyKwh: 80.0`
> **结果**：成功，新目标 80.0，预估总费用从 ~60 变为 ~77
> **前端操作**：
>
> - 显示"目标电量已更新为 80.0 kWh"
> - 更新本地缓存的新目标值
> - 预估结束时间刷新
> - 预估总费用刷新（用户可看到将会多花多少钱）

#### 场景 2：充电中调低电量（被拒绝）

> **前置状态**：`chargedEnergyKwh: 25.3, requestedEnergyKwh: 60.0`
> **请求**：`requestedEnergyKwh: 20.0`
> **响应**：
>
> ```json
> { "code": 400, "message": "新电量必须大于已充电量 25.3 kWh", "data": null }
> ```
>
> **前端操作**：
>
> - 前端已在本地校验，正常情况下不会发出此请求
> - 如收到此错误（边界情况），提示"新电量必须大于已充电量"
> - 将输入框的下限设置为 `chargedEnergyKwh + 0.1`

#### 场景 3：排队中修改电量

> **前置状态**：`status: "queued", chargedEnergyKwh: 0`
> **请求**：`requestedEnergyKwh: 50.0`
> **结果**：成功，新目标 50.0
> **前端操作**：更新显示即可，不影响排队位置

#### 场景 4：会话已结束不可修改

> **响应**：
>
> ```json
> { "code": 400, "message": "会话已结束，不可修改", "data": null }
> ```
>
> **前端操作**：提示"充电已结束，无法修改"

### 后置操作（操作契约）

| 步骤 | 操作                                                                     |
| ---- | ------------------------------------------------------------------------ |
| 1    | 前端更新本地缓存的目标电量值                                             |
| 2    | 充电态时，更新预估结束时间和预估总费用                                   |
| 3    | 充电态时，`estimatedTotalFee` 可展示给用户看："预计总共将花费 ¥77.32" |

---

## GET /sessions/:id/protocol-options — 获取候选充电协议

### 功能说明

获取当前会话可切换或可提交的充电协议列表。前端在展示协议修改弹窗前调用本接口，并使用返回列表作为用户候选范围。

### 请求格式

```
GET /api/v1/sessions/:id/protocol-options
Authorization: Bearer <token>
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 会话 ID |

### 前置条件（操作契约）

| 条件 | 说明                                                         |
| ---- | ------------------------------------------------------------ |
| 前端 | 当前会话状态为 `queued`、`waiting` 或 `charging`       |
| 系统 | 会话存在且属于当前用户                                       |
| 系统 | 根据用户注册协议、当前会话状态和当前充电桩协议实时计算候选项 |

### 响应字段

| 字段                    | 类型            | 始终返回 | 说明                    |
| ----------------------- | --------------- | -------- | ----------------------- |
| `sessionId`           | Number          | 是       | 会话 ID                 |
| `status`              | String          | 是       | 当前会话状态            |
| `selectedProtocolIds` | Array\<Number\> | 是       | 当前会话已选择的协议 ID |
| `options`             | Array           | 是       | 候选协议列表            |
| `options[].id`        | Number          | 是       | 协议 ID                 |
| `options[].name`      | String          | 是       | 协议名称                |
| `options[].powerKw`   | Number          | 是       | 功率（kW）              |

### 响应示例

```json
{
  "code": 200,
  "data": {
    "sessionId": 101,
    "status": "queued",
    "selectedProtocolIds": [1],
    "options": [
      {"id": 1, "name": "AC 7kW", "powerKw": 7.0},
      {"id": 3, "name": "DC 120kW", "powerKw": 120.0}
    ]
  }
}
```

### 后置操作（操作契约）

| 步骤 | 操作                                          |
| ---- | --------------------------------------------- |
| 1    | 前端展示 options 中的协议供用户选择           |
| 2    | 用户确认后调用 `PUT /sessions/:id/protocol` |

---

## PUT /sessions/:id/protocol — 修改支持的充电协议

### 功能说明

修改该充电会话支持的充电协议列表。排队/等待态可在 `GET /sessions/:id/protocol-options` 返回范围内选择；充电态只能在当前桩支持的协议中切换。系统在提交时重新校验协议可用性。

### 请求格式

```
PUT /api/v1/sessions/:id/protocol
Authorization: Bearer <token>
Content-Type: application/json
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 会话 ID |

### 请求字段

| 字段            | 类型            | 必填 | 说明                        |
| --------------- | --------------- | ---- | --------------------------- |
| `protocolIds` | Array\<Number\> | 是   | 新的协议 ID 列表，至少 1 个 |

### 请求示例

```json
{
  "protocolIds": [1, 3]
}
```

### 前置条件（操作契约）

| 条件 | 说明                                                     |
| ---- | -------------------------------------------------------- |
| 前端 | 调用 `GET /sessions/:id/protocol-options` 获取候选协议 |
| 前端 | 用户只能提交 options 中包含的协议 ID                     |
| 前端 | protocolIds 非空                                         |
| 系统 | 排队/等待态：所有 protocolIds 必须在用户注册范围内       |
| 系统 | 充电态：所有 protocolIds 必须在当前桩支持的范围内        |
| 系统 | 充电态：至少保留一个协议（不能移除全部）                 |
| 系统 | 提交时重新计算候选协议范围并完成二次校验                 |

### 响应字段

| 字段                   | 类型   | 始终返回 | 说明                                                        |
| ---------------------- | ------ | -------- | ----------------------------------------------------------- |
| `sessionId`          | Number | 是       | 会话 ID                                                     |
| `supportedProtocols` | Array  | 是       | 更新后的协议列表                                            |
| `chargedEnergyKwh`   | Number | 是       | 当前已充电量                                                |
| `currentFee`         | Object | 是       | 实时费用快照（同 `GET /sessions/:id` 中 currentFee 结构） |

### 响应示例

```json
{
  "code": 200,
  "message": "充电协议已更新",
  "data": {
    "sessionId": 101,
    "supportedProtocols": [
      {"id": 1, "name": "AC 7kW", "powerKw": 7.0},
      {"id": 3, "name": "DC 120kW", "powerKw": 120.0}
    ],
    "chargedEnergyKwh": 25.3,
    "currentFee": {
      "electricityFee": 20.24,
      "baseServiceFee": 5.00,
      "timeServiceFee": 1.88,
      "totalServiceFee": 6.88,
      "totalFee": 27.12
    }
  }
}
```

### 场景示例

#### 场景 1：排队中增加支持的协议

> **前置**：现在只支持 AC 7kW，想增加 DC 120kW
> **请求**：`protocolIds: [1, 3]`
> **效果**：进入充电时，系统可使用 DC 120kW 提高充电速度
> **前端**：更新协议标签显示

#### 场景 2：充电中切换协议（仅切换当前使用的）

> **前置**：使用的是 DC 120kW，想切到 AC 7kW
> **注意**：充电态的协议切换会**立即生效**，当前使用的协议变为新协议，之后的充电功率按新协议计算
> **前端**：提示用户"切换协议后充电速度将变化"

#### 场景 3：充电中移除当前使用的协议（被拒绝）

> **前置**：当前使用 DC 120kW (id:3)
> **请求**：`protocolIds: [1]`（移除了 3）
> **响应**：
>
> ```json
> { "code": 400, "message": "充电中不能移除当前使用的协议 DC 120kW", "data": null }
> ```
>
> **前端操作**：提示"当前正在使用此协议充电，不能移除"

### 后置操作（操作契约）

| 步骤 | 操作                                     |
| ---- | ---------------------------------------- |
| 1    | 前端更新本地缓存的协议列表               |
| 2    | 充电态切换协议时，更新界面上当前协议显示 |

---

## GET /sessions/:id/switch-options — 获取可换入充电桩

### 功能说明

获取当前会话可换入的充电桩列表。前端在展示换队弹窗前调用本接口，并使用返回列表作为用户候选范围。

### 请求格式

```
GET /api/v1/sessions/:id/switch-options
Authorization: Bearer <token>
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 会话 ID |

### 前置条件（操作契约）

| 条件 | 说明                                                         |
| ---- | ------------------------------------------------------------ |
| 前端 | 当前会话状态为 `queued`                                    |
| 系统 | 会话存在且属于当前用户                                       |
| 系统 | 根据当前会话协议、充电桩状态和排队区容量实时计算可换入充电桩 |

### 响应字段

| 字段                 | 类型   | 始终返回 | 说明             |
| -------------------- | ------ | -------- | ---------------- |
| `sessionId`        | Number | 是       | 会话 ID          |
| `currentStationId` | Number | 是       | 当前充电桩 ID    |
| `options`          | Array  | 是       | 可换入充电桩列表 |
| `options[].id`     | Number | 是       | 充电桩 ID        |
| `options[].name`   | String | 是       | 充电桩名称       |
| `options[].status` | String | 是       | 充电桩状态       |

### 响应示例

```json
{
  "code": 200,
  "data": {
    "sessionId": 101,
    "currentStationId": 1,
    "options": [
      {"id": 2, "name": "B区-02号桩", "status": "running"},
      {"id": 3, "name": "C区-03号桩", "status": "running"}
    ]
  }
}
```

### 后置操作（操作契约）

| 步骤 | 操作                                                 |
| ---- | ---------------------------------------------------- |
| 1    | 前端展示 options 中的充电桩供用户选择                |
| 2    | 用户确认后调用 `POST /sessions/:id/switch-station` |

---

## POST /sessions/:id/switch-station — 换到其他桩排队

### 功能说明

将车辆从当前排队区转移到目标充电桩的排队区队尾。**仅在排队区（queued）时可操作**，等待区不可换队。前端先调用 `GET /sessions/:id/switch-options` 获取可换入充电桩，用户选择后提交本接口。

### 请求格式

```
POST /api/v1/sessions/:id/switch-station
Authorization: Bearer <token>
Content-Type: application/json
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 会话 ID |

### 请求字段

| 字段                | 类型   | 必填 | 说明                            |
| ------------------- | ------ | ---- | ------------------------------- |
| `targetStationId` | Number | 是   | 目标充电桩 ID，不能与当前桩相同 |

### 请求示例

```json
{
  "targetStationId": 2
}
```

### 前置条件（操作契约）

| 条件 | 说明                                                           |
| ---- | -------------------------------------------------------------- |
| 前端 | 必须确保当前状态为 `queued`（从 `GET /sessions/:id` 获取） |
| 前端 | 调用 `GET /sessions/:id/switch-options` 获取可换入充电桩     |
| 前端 | 目标桩必须来自 switch-options 的 options 列表                  |
| 系统 | 当前会话状态必须是 `queued`                                  |
| 系统 | 目标充电桩状态必须是 `running`                               |
| 系统 | 目标排队区有空位（queueCount < queueCapacity）                 |
| 系统 | 提交时重新计算可换入充电桩范围并完成二次校验                   |

### 响应字段

| 字段                     | 类型   | 始终返回 | 说明                 |
| ------------------------ | ------ | -------- | -------------------- |
| `sessionId`            | Number | 是       | 会话 ID              |
| `stationId`            | Number | 是       | 新充电桩 ID          |
| `zone`                 | String | 是       | `queue`            |
| `queuePosition`        | Number | 是       | 在新队列中的位置     |
| `estimatedWaitMinutes` | Number | 是       | 在新桩的预估等待时间 |

### 响应示例

```json
{
  "code": 200,
  "message": "已更换到目标充电桩",
  "data": {
    "sessionId": 101,
    "stationId": 2,
    "zone": "queue",
    "queuePosition": 5,
    "estimatedWaitMinutes": 20
  }
}
```

### 场景示例

#### 场景 1：正常换队

> **前置**：当前在 1 号桩排队第 3 位，发现 2 号桩排队更快
> **请求**：`targetStationId: 2`
> **结果**：成功换到 2 号桩队尾第 5 位
> **前端操作**：
>
> - 更新显示的充电桩名称和排队位置
> - `GET /sessions/:id` 轮询的下一次响应也会更新为新桩的数据
> - 提示"已换到 B 区-02 号桩"

#### 场景 2：目标桩排队区已满

> **响应**：
>
> ```json
> { "code": 400, "message": "目标充电桩排队区已满，无法换队", "data": null }
> ```
>
> **前端操作**：提示用户"该桩已满，请选择其他充电桩"，不关闭选择列表

#### 场景 3：等待区中尝试换队（被拒绝）

> **请求**：当前状态是 waiting
> **响应**：
>
> ```json
> { "code": 400, "message": "等待区中不可换队", "data": null }
> ```
>
> **前端操作**：前端应在状态为 `waiting` 时隐藏"换队"按钮，仅显示"取消"

#### 场景 4：目标桩已停止

> **响应**：
>
> ```json
> { "code": 400, "message": "目标充电桩已停止运行，无法换队", "data": null }
> ```
>
> **前端操作**：提示用户，并重新调用 `GET /sessions/:id/switch-options` 获取可换入充电桩

### 后置操作（操作契约）

| 步骤 | 操作                                                   |
| ---- | ------------------------------------------------------ |
| 1    | 前端更新 station 和 queuePosition 的本地缓存           |
| 2    | `GET /sessions/:id` 轮询继续，后续响应指向新桩的数据 |
| 3    | 前端可刷新桩列表 UI                                    |

---

## POST /sessions/:id/cancel — 取消充电

### 功能说明

取消充电会话。根据当前所在区域决定是否收费。

| 取消时状态             | 费用       | 说明                    |
| ---------------------- | ---------- | ----------------------- |
| `queued`（排队区）   | 免费       | 未占用资源              |
| `waiting`（等待区）  | 基础服务费 | 已占用等待位资源        |
| 充电确认阶段超时/拒绝  | 基础服务费 | 可配置，每个桩可不同    |
| `charging`（充电中） | 不可取消   | 须用 stop-charging 接口 |

### 请求格式

```
POST /api/v1/sessions/:id/cancel
Authorization: Bearer <token>
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 会话 ID |

### 前置条件（操作契约）

| 条件 | 说明                                                                                  |
| ---- | ------------------------------------------------------------------------------------- |
| 前端 | 在排队态时：取消按钮文案为"取消排队"，提示"免费取消"                                  |
| 前端 | 在等待态时：取消按钮文案为"退出充电"，提示"将收取基础服务费 ¥5.00"，需要二次确认弹窗 |
| 系统 | 会话状态为 {queued, waiting}（charging 态需用 stop-charging）                         |

### 响应字段

| 字段                    | 类型         | 始终返回 | 条件说明                          |
| ----------------------- | ------------ | -------- | --------------------------------- |
| `sessionId`           | Number       | 是       | 会话 ID                           |
| `status`              | String       | 是       | `cancelled`                     |
| `message`             | String       | 是       | 提示信息                          |
| `bill`                | Object\|null | 仅收费时 | 收费时返回账单摘要，免费时为 null |
| `bill.billId`         | Number       | -        | 账单 ID                           |
| `bill.baseServiceFee` | Number       | -        | 基础服务费                        |
| `bill.totalFee`       | Number       | -        | 总费用                            |

### 响应示例

#### 排队区取消 — 免费

```json
{
  "code": 200,
  "message": "已取消，无费用",
  "data": {
    "sessionId": 101,
    "status": "cancelled",
    "message": "已取消，无费用",
    "bill": null
  }
}
```

#### 等待区取消 — 收基础服务费

```json
{
  "code": 200,
  "message": "已取消，需支付基础服务费 ¥5.00",
  "data": {
    "sessionId": 101,
    "status": "cancelled",
    "message": "已取消，需支付基础服务费 ¥5.00",
    "bill": {
      "billId": 1,
      "baseServiceFee": 5.00,
      "totalFee": 5.00,
      "paymentStatus": "unpaid"
    }
  }
}
```

### 场景示例

#### 场景 1：排队中取消（免费）

> **前端操作**：
>
> 1. 用户点击"取消排队"
> 2. 弹窗确认："确定要取消排队吗？当前免费取消"
> 3. 用户确认后调用接口
> 4. 收到免费响应 → 停止轮询 → 显示"已取消" → 跳转主页
> 5. 无需支付流程

#### 场景 2：等待中取消（收费）

> **前端操作**：
>
> 1. 用户点击"退出充电"
> 2. 弹窗二次确认："退出将收取基础服务费 ¥5.00，确定退出吗？"
> 3. 用户确认后调用接口
> 4. 收到收费响应 → 停止轮询 → 跳转支付页（展示 ¥5.00 待支付）
> 5. 必须完成支付

#### 场景 3：充电中尝试取消（被拒绝）

> **响应**：
>
> ```json
> { "code": 400, "message": "充电中不可取消，请使用停止充电接口", "data": null }
> ```
>
> **前端操作**：前端应在充电态隐藏"取消"按钮，只显示"停止充电"

### 后置操作（操作契约）

| 情况     | 操作                                               |
| -------- | -------------------------------------------------- |
| 免费取消 | 停止轮询，跳转主页，展示"已取消"提示               |
| 收费取消 | 停止轮询，跳转支付页，展示 billId 和金额，引导支付 |

---

## POST /sessions/:id/confirm-charging — 确认/拒绝开始充电

### 功能说明

车辆被系统自动调度到充电区后，系统请求用户确认充电协议和电量。
用户可在此步骤调整充电协议和电量，确认后开始计费。超时未确认则自动取消。

### 请求格式

```
POST /api/v1/sessions/:id/confirm-charging
Authorization: Bearer <token>
Content-Type: application/json
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 会话 ID |

### 请求字段

| 字段                   | 类型   | 必填                  | 说明                                             |
| ---------------------- | ------ | --------------------- | ------------------------------------------------ |
| `action`             | String | 是                    | `confirm`（确认开始）或 `reject`（拒绝取消） |
| `protocolId`         | Number | action=confirm 时必填 | 选择的充电协议 ID，必须在桩支持的范围内          |
| `requestedEnergyKwh` | Number | 否                    | 可在此修改目标电量，不传则使用原值               |

### 请求示例

```json
{
  "action": "confirm",
  "protocolId": 3,
  "requestedEnergyKwh": 60.0
}
```

### 前置条件（操作契约）

| 条件 | 说明                                                      |
| ---- | --------------------------------------------------------- |
| 前端 | 进入充电区后，前端应立即弹出确认界面                      |
| 前端 | 显示推荐协议（最高功率的兼容协议），允许用户切换          |
| 前端 | 显示当前目标电量，允许用户修改                            |
| 前端 | **设置超时倒计时**（如 60 秒），超时自动提交 reject |
| 系统 | 会话状态为刚刚进入充电区（尚未开始充电）                  |

### 响应字段（confirm）

| 字段                  | 类型   | 始终返回 | 说明         |
| --------------------- | ------ | -------- | ------------ |
| `sessionId`         | Number | 是       | 会话 ID      |
| `status`            | String | 是       | `charging` |
| `protocol`          | Object | 是       | 选择的协议   |
| `startedChargingAt` | String | 是       | 开始充电时间 |
| `message`           | String | 是       | 提示信息     |

### 响应字段（reject/超时）

| 字段          | 类型   | 始终返回 | 说明                 |
| ------------- | ------ | -------- | -------------------- |
| `sessionId` | Number | 是       | 会话 ID              |
| `status`    | String | 是       | `cancelled`        |
| `bill`      | Object | 是       | 账单（含基础服务费） |
| `message`   | String | 是       | 提示信息             |

### 响应示例

#### 确认成功

```json
{
  "code": 200,
  "message": "开始充电",
  "data": {
    "sessionId": 101,
    "status": "charging",
    "protocol": {"id": 3, "name": "DC 120kW", "powerKw": 120.0},
    "startedChargingAt": "2026-06-08T14:05:00",
    "message": "开始充电"
  }
}
```

#### 拒绝/超时

```json
{
  "code": 200,
  "message": "已取消，需支付基础服务费 ¥5.00",
  "data": {
    "sessionId": 101,
    "status": "cancelled",
    "bill": {
      "billId": 1,
      "baseServiceFee": 5.00,
      "totalFee": 5.00,
      "paymentStatus": "unpaid"
    },
    "message": "已取消，需支付基础服务费 ¥5.00"
  }
}
```

### 场景示例

#### 场景 1：确认开始充电

> **前端操作**：
>
> 1. 显示确认界面："已轮到您充电！请确认以下信息："
> 2. 协议选择器（默认最高功率兼容协议）
> 3. 电量输入框（默认原目标电量）
> 4. 倒计时 60 秒
> 5. 用户点击"确认开始"
> 6. 收到 `status: "charging"` → 跳转充电进度页 → 开始轮询

#### 场景 2：超时未确认

> **前端操作**：
>
> 1. 倒计时归零，前端自动提交 `action: "reject"`
> 2. 收到 `status: "cancelled"` → 跳转支付页（基础服务费）
>    **处理结果**：用户离开后充电位不会被无限占用

#### 场景 3：手动拒绝

> **前端操作**：
>
> 1. 用户点击"不使用，退出"
> 2. 二次确认弹窗："退出将收取基础服务费 ¥5.00"
> 3. 用户确认后提交 `action: "reject"`
> 4. 收到取消响应 → 跳转支付页

### 后置操作（操作契约）

| 结果         | 操作                                             |
| ------------ | ------------------------------------------------ |
| confirm 成功 | 跳转充电进度页，启动 `GET /sessions/:id` 轮询  |
| reject/超时  | 停止轮询（若有），跳转支付页，展示 billId 和金额 |

---

## POST /sessions/:id/stop-charging — 结束充电

### 功能说明

手动停止正在进行的充电。充电完成或被用户主动中断时调用。结束后自动生成账单。

### 请求格式

```
POST /api/v1/sessions/:id/stop-charging
Authorization: Bearer <token>
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 会话 ID |

### 前置条件（操作契约）

| 条件 | 说明                                                                         |
| ---- | ---------------------------------------------------------------------------- |
| 前端 | 只有当前状态为 `charging` 时显示"停止充电"按钮                             |
| 前端 | 点击后应弹窗二次确认："确定要停止充电吗？已充电量 X.X kWh，将按实际用量计费" |
| 系统 | 会话状态必须是 `charging`                                                  |

### 响应字段

| 字段                        | 类型   | 始终返回 | 说明          |
| --------------------------- | ------ | -------- | ------------- |
| `sessionId`               | Number | 是       | 会话 ID       |
| `status`                  | String | 是       | `completed` |
| `chargedEnergyKwh`        | Number | 是       | 实际充电量    |
| `requestedEnergyKwh`      | Number | 是       | 目标电量      |
| `bill`                    | Object | 是       | 完整账单      |
| `bill.billId`             | Number | 是       | 账单 ID       |
| `bill.electricityFee`     | Number | 是       | 电费          |
| `bill.electricityDetails` | Array  | 是       | 分时段明细    |
| `bill.baseServiceFee`     | Number | 是       | 基础服务费    |
| `bill.timeServiceFee`     | Number | 是       | 时长服务费    |
| `bill.totalServiceFee`    | Number | 是       | 服务费合计    |
| `bill.totalFee`           | Number | 是       | 总费用        |
| `bill.paymentStatus`      | String | 是       | `unpaid`    |

### 响应示例

```json
{
  "code": 200,
  "message": "充电已结束",
  "data": {
    "sessionId": 101,
    "status": "completed",
    "chargedEnergyKwh": 45.2,
    "requestedEnergyKwh": 60.0,
    "bill": {
      "billId": 1,
      "electricityFee": 36.16,
      "electricityDetails": [
        {"period": "峰时", "energy": 10.0, "price": 1.2, "fee": 12.0},
        {"period": "平时", "energy": 35.2, "price": 0.8, "fee": 28.16}
      ],
      "baseServiceFee": 5.00,
      "timeServiceFee": 6.75,
      "totalServiceFee": 11.75,
      "totalFee": 47.91,
      "paymentStatus": "unpaid"
    }
  }
}
```

### 场景示例

#### 场景 1：用户主动停止（未充满）

> **前置**：charing，60%，用户有急事提前走
> **前端操作**：
>
> 1. 点击"停止充电"
> 2. 确认弹窗："已充电 27.5 kWh，确定停止吗？"
> 3. 调用接口
> 4. 收到 completed → 停止轮询 → 跳转支付页展示最终账单

#### 场景 2：电量已充满（自动触发的等效结果）

> **注意**：自动充满由系统触发，不经过此接口。
> 前端通过 `GET /sessions/:id` 收到 `status: "completed"` 来感知。
> 此接口仅用于**用户手动提前结束**。

#### 场景 3：排队中尝试停止（被拒绝）

> **响应**：
>
> ```json
> { "code": 400, "message": "当前不在充电状态", "data": null }
> ```
>
> **前端操作**：前端应在非充电态隐藏"停止充电"按钮

### 后置操作（操作契约）

| 步骤 | 操作                                                |
| ---- | --------------------------------------------------- |
| 1    | 前端停止 `GET /sessions/:id` 轮询（如果还在轮询） |
| 2    | 跳转支付页面，展示 bill 中的完整账单信息            |
| 3    | 用户确认后调用 POST /bills/:id/pay                  |

---

# 第四部分：账单模块

## GET /bills — 查看我的历史账单

### 功能说明

获取当前用户的历史账单列表。系统根据 Authorization 中的用户身份查询该用户名下账单，默认按 `createdAt` 倒序返回，最新账单在前。

### 请求格式

```
GET /api/v1/bills?page=1&pageSize=20&paymentStatus=paid&startDate=2026-01-01&endDate=2026-06-08
Authorization: Bearer <token>
```

### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | Number | 否 | 页码，默认 1 |
| `pageSize` | Number | 否 | 每页数量，默认 20 |
| `paymentStatus` | String | 否 | `unpaid` / `paid` |
| `startDate` | String | 否 | 开始日期 `yyyy-MM-dd` |
| `endDate` | String | 否 | 结束日期 `yyyy-MM-dd` |

### 前置条件（操作契约）

| 条件 | 说明 |
|------|------|
| 前端 | 必须已登录，携带有效 token |
| 系统 | 仅返回当前用户所属账单 |

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `list` | Array | 账单列表 |
| `list[].billId` | Number | 账单 ID |
| `list[].sessionId` | Number | 关联会话 ID |
| `list[].station` | Object | 充电桩摘要 |
| `list[].station.id` | Number | 充电桩 ID |
| `list[].station.name` | String | 充电桩名称 |
| `list[].chargingDuration` | String | 充电时长 `HH:mm:ss` |
| `list[].chargedEnergyKwh` | Number | 实际充电量 |
| `list[].totalFee` | Number | 总费用 |
| `list[].paymentStatus` | String | `unpaid` / `paid` |
| `list[].createdAt` | String | 创建时间 |
| `list[].paidAt` | String\|null | 支付时间 |
| `page` | Number | 当前页码 |
| `pageSize` | Number | 每页数量 |
| `total` | Number | 总数量 |

### 响应示例

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "billId": 1,
        "sessionId": 101,
        "station": {"id": 1, "name": "A区-01号桩"},
        "chargingDuration": "00:45:00",
        "chargedEnergyKwh": 45.2,
        "totalFee": 47.91,
        "paymentStatus": "paid",
        "createdAt": "2026-06-08T14:50:00",
        "paidAt": "2026-06-08T14:52:00"
      }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 1
  }
}
```

### 场景示例

#### 场景 1：用户查看历史账单

> **前端操作**：展示账单列表，用户点击某一项后调用 `GET /bills/:id` 查看账单详情。

#### 场景 2：用户按支付状态筛选

> **请求**：`paymentStatus=unpaid`
> **前端操作**：展示当前用户未支付账单列表，并在列表项中显示支付入口。

### 后置操作（操作契约）

| 步骤 | 操作 |
|------|------|
| 1 | 前端渲染当前用户历史账单列表 |
| 2 | 用户点击账单项后调用 `GET /bills/:id` |

---

## GET /bills/:id — 查看账单详情

### 功能说明

获取当前用户单张账单的完整信息，包括分时电费明细、服务费阶梯明细。

### 请求格式

```
GET /api/v1/bills/:id
Authorization: Bearer <token>
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 账单 ID |

### 前置条件（操作契约）

| 条件 | 说明                                                                       |
| ---- | -------------------------------------------------------------------------- |
| 前端 | 在 `GET /sessions/:id` 轮询到 completed/cancelled 后，或支付页刷新时调用 |
| 系统 | 账单存在且属于当前用户                                                     |

> **处理说明**：会话完成或取消后，前端从 `GET /sessions/:id` 响应中的 `bill.billId` 取得账单 ID，并调用本接口获取完整账单详情。本接口也用于历史账单列表点击后的详情查看。

### 响应字段

| 字段                            | 类型         | 说明                  |
| ------------------------------- | ------------ | --------------------- |
| `id`                          | Number       | 账单 ID               |
| `sessionId`                   | Number       | 关联会话 ID           |
| `user`                        | Object       | 用户摘要              |
| `user.id`                     | Number       | 用户 ID               |
| `user.licensePlate`           | String       | 车牌号                |
| `station`                     | Object       | 充电桩摘要            |
| `station.id`                  | Number       | 桩 ID                 |
| `station.name`                | String       | 桩名称                |
| `chargingDuration`            | String       | 充电时长 `HH:mm:ss` |
| `chargingMinutes`             | Number       | 充电总分钟数          |
| `chargedEnergyKwh`            | Number       | 实际充电量            |
| `electricityFee`              | Number       | 电费合计              |
| `electricityDetails`          | Array        | 各时段电量电价明细    |
| `electricityDetails[].period` | String       | 时段名称              |
| `electricityDetails[].energy` | Number       | 该时段充电量          |
| `electricityDetails[].price`  | Number       | 该时段电价            |
| `electricityDetails[].fee`    | Number       | 该时段电费            |
| `baseServiceFee`              | Number       | 基础服务费            |
| `serviceFeeTiers`             | Array        | 服务费阶梯明细        |
| `serviceFeeTiers[].tier`      | String       | 阶梯名称              |
| `serviceFeeTiers[].minutes`   | Number       | 该阶梯分钟数          |
| `serviceFeeTiers[].rate`      | Number       | 该阶梯费率            |
| `serviceFeeTiers[].fee`       | Number       | 该阶梯费用            |
| `timeServiceFee`              | Number       | 时长服务费合计        |
| `totalServiceFee`             | Number       | 服务费合计            |
| `totalFee`                    | Number       | **总费用**      |
| `paymentStatus`               | String       | `unpaid` / `paid` |
| `createdAt`                   | String       | 创建时间              |
| `paidAt`                      | String\|null | 支付时间              |

### 响应示例

```json
{
  "code": 200,
  "data": {
    "id": 1,
    "sessionId": 101,
    "user": {"id":1, "licensePlate":"京A12345"},
    "station": {"id":1, "name":"A区-01号桩"},
    "chargingDuration": "00:45:00",
    "chargingMinutes": 45,
    "chargedEnergyKwh": 45.2,
    "electricityFee": 36.16,
    "electricityDetails": [
      {"period": "峰时(08:00-11:00)", "energy": 10.0, "price": 1.2, "fee": 12.0},
      {"period": "平时(11:00-18:00)", "energy": 35.2, "price": 0.8, "fee": 28.16}
    ],
    "baseServiceFee": 5.00,
    "serviceFeeTiers": [
      {"tier": "0-60分钟", "minutes": 45, "rate": 0.15, "fee": 6.75}
    ],
    "timeServiceFee": 6.75,
    "totalServiceFee": 11.75,
    "totalFee": 47.91,
    "paymentStatus": "unpaid",
    "createdAt": "2026-06-08T14:50:00",
    "paidAt": null
  }
}
```

### 场景示例

#### 场景 1：用户查看完整账单

> **前端操作**：
>
> - 显示充电桩名称、充电时长
> - 电费区域：展示峰时/平时/谷时的电量、电价、费用
> - 服务费区域：展示基础费、各阶梯时长费率
> - 底部：合计总费用、支付按钮

#### 场景 2：账单已支付

```json
{
  "code": 200,
  "data": {
    "totalFee": 47.91,
    "paymentStatus": "paid",
    "paidAt": "2026-06-08T14:52:00",
    "transactionId": "TXN2026060814520001"
  }
}
```

> **前端操作**：显示"已支付"状态，展示交易流水号

#### 场景 3：账单不属于当前用户

> **响应**：
>
> ```json
> { "code": 403, "message": "无权访问该账单", "data": null }
> ```

### 后置操作（操作契约）

| 状态       | 操作                               |
| ---------- | ---------------------------------- |
| `unpaid` | 显示支付按钮，引导用户支付         |
| `paid`   | 显示已支付状态，可关闭页面返回主页 |

---

## POST /bills/:id/pay — 模拟支付

### 功能说明

模拟支付流程，标记账单为已支付状态。用于演示和测试。

### 请求格式

```
POST /api/v1/bills/:id/pay
Authorization: Bearer <token>
Content-Type: application/json
```

| 参数   | 位置 | 类型   | 必填 | 说明    |
| ------ | ---- | ------ | ---- | ------- |
| `id` | Path | Number | 是   | 账单 ID |

### 请求字段

| 字段              | 类型   | 必填 | 说明                                         |
| ----------------- | ------ | ---- | -------------------------------------------- |
| `paymentMethod` | String | 是   | 支付方式：`wechat` / `alipay` / `card` |

### 请求示例

```json
{
  "paymentMethod": "wechat"
}
```

### 前置条件（操作契约）

| 条件 | 说明                                                      |
| ---- | --------------------------------------------------------- |
| 前端 | 展示支付方式选择（微信/支付宝/银行卡），确保用户先选择    |
| 前端 | 支付按钮在点击后应置灰并显示"支付处理中..."，限制重复点击 |
| 系统 | 账单存在、属于当前用户、且 `paymentStatus = "unpaid"`   |

### 响应字段

| 字段              | 类型   | 说明           |
| ----------------- | ------ | -------------- |
| `billId`        | Number | 账单 ID        |
| `paymentStatus` | String | `paid`       |
| `totalFee`      | Number | 支付金额       |
| `paidAt`        | String | 支付时间       |
| `transactionId` | String | 模拟交易流水号 |

### 响应示例

```json
{
  "code": 200,
  "message": "支付成功",
  "data": {
    "billId": 1,
    "paymentStatus": "paid",
    "totalFee": 47.91,
    "paidAt": "2026-06-08T14:52:00",
    "transactionId": "TXN2026060814520001"
  }
}
```

### 场景示例

#### 场景 1：正常支付

> **前端操作**：
>
> 1. 用户选择支付方式（如微信）
> 2. 点击"确认支付 ¥47.91"
> 3. 按钮变为"支付中..."，不可重复点击
> 4. 收到支付成功 → 显示"支付成功"动画
> 5. 展示交易流水号和支付时间
> 6. 提供"返回主页"按钮

#### 场景 2：账单已支付（重复支付）

> **响应**：
>
> ```json
> { "code": 400, "message": "该账单已支付", "data": null }
> ```
>
> **前端操作**：提示"该账单已支付"，跳转到账单详情页

#### 场景 3：被取消的账单不需要支付

> 注意：等待区取消产生的仅基础服务费账单也需支付。
> **前端操作**：无论金额大小，都需要完成支付流程。

### 后置操作（操作契约）

| 步骤 | 操作                               |
| ---- | ---------------------------------- |
| 1    | 前端显示"支付成功"页面             |
| 2    | 展示交易流水号、支付时间、支付金额 |
| 3    | 提供"返回主页"按钮                 |

---

# 第五部分：管理员接口

## 全局配置

### GET /admin/config — 获取全局配置

**功能**：获取所有全局配置，包括当前调度算法、服务费标准、电价配置。

```
GET /api/v1/admin/config
Authorization: Bearer <admin_token>
```

**响应字段**：

| 字段                                | 类型         | 说明                    |
| ----------------------------------- | ------------ | ----------------------- |
| `schedulingAlgorithm`             | String       | 当前调度算法标识        |
| `baseServiceFee`                  | Number       | 全局基础服务费（元）    |
| `serviceFeeTiers`                 | Array        | 服务费阶梯费率配置      |
| `serviceFeeTiers[].minMinutes`    | Number       | 最小分钟数              |
| `serviceFeeTiers[].maxMinutes`    | Number\|null | 最大分钟数（null=无限） |
| `serviceFeeTiers[].ratePerMinute` | Number       | 费率（元/分钟）         |
| `electricityPrices`               | Array        | 分时电价配置            |
| `electricityPrices[].periodName`  | String       | 时段名称                |
| `electricityPrices[].start`       | String       | 开始时间 `HH:mm`      |
| `electricityPrices[].end`         | String       | 结束时间 `HH:mm`      |
| `electricityPrices[].pricePerKwh` | Number       | 电价                    |

---

### PUT /admin/config — 更新全局配置

**功能**：统一更新全局配置参数。管理端配置页使用一个保存按钮提交本接口。

```
PUT /api/v1/admin/config
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**请求字段**（全部可选，只传需要修改的字段）：

| 字段                                | 类型         | 说明                                                                                               |
| ----------------------------------- | ------------ | -------------------------------------------------------------------------------------------------- |
| `schedulingAlgorithm`             | String       | `shortest_time_single` / `batch_shortest` / `priority` / `time_order` / `fault_recovery` |
| `baseServiceFee`                  | Number       | 基础服务费（元）                                                                                   |
| `electricityPrices`               | Array        | 分时电价配置列表，全量替换                                                                         |
| `electricityPrices[].periodName`  | String       | 时段名称                                                                                           |
| `electricityPrices[].start`       | String       | 开始时间 `HH:mm`                                                                                 |
| `electricityPrices[].end`         | String       | 结束时间 `HH:mm`                                                                                 |
| `electricityPrices[].pricePerKwh` | Number       | 电价                                                                                               |
| `serviceFeeTiers`                 | Array        | 服务费阶梯费率列表，全量替换                                                                       |
| `serviceFeeTiers[].tierName`      | String       | 阶梯名称                                                                                           |
| `serviceFeeTiers[].minMinutes`    | Number       | 最小分钟数（含）                                                                                   |
| `serviceFeeTiers[].maxMinutes`    | Number\|null | 最大分钟数（不含，null=无限）                                                                      |
| `serviceFeeTiers[].ratePerMinute` | Number       | 费率（元/分钟）                                                                                    |

**请求示例**：

```json
{
  "schedulingAlgorithm": "shortest_time_single",
  "baseServiceFee": 5.00,
  "electricityPrices": [
    {"periodName": "峰时", "start": "08:00", "end": "11:00", "pricePerKwh": 1.2},
    {"periodName": "平时", "start": "11:00", "end": "18:00", "pricePerKwh": 0.8},
    {"periodName": "谷时", "start": "18:00", "end": "08:00", "pricePerKwh": 0.4}
  ],
  "serviceFeeTiers": [
    {"tierName": "0-60分钟", "minMinutes": 0, "maxMinutes": 60, "ratePerMinute": 0.15},
    {"tierName": "60分钟以上", "minMinutes": 60, "maxMinutes": null, "ratePerMinute": 0.20}
  ]
}
```

**响应字段**：返回更新后的完整全局配置，字段同 `GET /admin/config`。

---

## 充电桩管理

### POST /admin/stations — 创建充电桩

```
POST /api/v1/admin/stations
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**请求字段**：

| 字段                 | 类型            | 必填 | 说明                              |
| -------------------- | --------------- | ---- | --------------------------------- |
| `name`             | String          | 是   | 充电桩名称                        |
| `queueCapacity`    | Number          | 是   | 排队区容量                        |
| `waitingCapacity`  | Number          | 是   | 等待区容量                        |
| `chargingCapacity` | Number          | 是   | 充电区容量                        |
| `protocolIds`      | Array\<Number\> | 是   | 支持的协议 ID 列表                |
| `baseServiceFee`   | Number\|null    | 否   | 本桩独立基础服务费，null=使用全局 |

---

### PUT /admin/stations/:id — 修改充电桩配置

```
PUT /api/v1/admin/stations/:id
Authorization: Bearer <admin_token>
```

**请求字段**（全部可选，只传需要修改的字段）：

| 字段                 | 类型            | 说明                       |
| -------------------- | --------------- | -------------------------- |
| `name`             | String          | 充电桩名称                 |
| `queueCapacity`    | Number          | 排队区容量（运行中可调整） |
| `waitingCapacity`  | Number          | 等待区容量                 |
| `chargingCapacity` | Number          | 充电区容量                 |
| `protocolIds`      | Array\<Number\> | 支持的协议                 |
| `baseServiceFee`   | Number\|null    | 本桩独立基础服务费         |

> **注意**：修改容量时，如果减少后的容量小于当前已有车辆数，操作会被拒绝。

---

### DELETE /admin/stations/:id — 删除充电桩

```
DELETE /api/v1/admin/stations/:id
Authorization: Bearer <admin_token>
```

**前置条件**：

- 三个区域均无车辆（queueCount = 0, waitingCount = 0, chargingCount = 0）
- 不满足时返回 400，提示各区域的车辆数

---

### POST /admin/stations/:id/start — 启动充电桩

```
POST /api/v1/admin/stations/:id/start
Authorization: Bearer <admin_token>
```

> 将状态从 `stopped` 或 `error` 切换为 `running`。

---

### POST /admin/stations/:id/stop — 正常停止

```
POST /api/v1/admin/stations/:id/stop
Authorization: Bearer <admin_token>
```

> 不再接受新的充电请求。排队区车辆继续处理直到清空，然后自动切换为 `stopped`。

---

### POST /admin/stations/:id/emergency-stop — 异常停止

**功能**：所有排队/等待中的车辆按照指定算法重新调度到其他充电桩。正在充电的车辆继续充电到完成。

```
POST /api/v1/admin/stations/:id/emergency-stop
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**请求字段**：

| 字段                  | 类型            | 必填 | 说明                                                                                                             |
| --------------------- | --------------- | ---- | ---------------------------------------------------------------------------------------------------------------- |
| `algorithm`         | String          | 是   | 调度算法标识：`shortest_time_single` / `batch_shortest` / `priority` / `time_order` / `fault_recovery` |
| `excludeStationIds` | Array\<Number\> | 否   | 排除的充电桩 ID 列表                                                                                             |

**响应字段**：

| 字段                                    | 类型   | 说明                      |
| --------------------------------------- | ------ | ------------------------- |
| `message`                             | String | 提示信息                  |
| `status`                              | String | `stopped`               |
| `algorithm`                           | String | 使用的算法                |
| `redistributedSessions`               | Array  | 被重新调度的排队/等待车辆 |
| `redistributedSessions[].sessionId`   | Number | 会话 ID                   |
| `redistributedSessions[].fromStation` | String | 原充电桩名称              |
| `redistributedSessions[].toStation`   | String | 目标充电桩名称            |
| `redistributedSessions[].newPosition` | Number | 新队列位置                |
| `chargingSessions`                    | Array  | 继续充电的车辆            |
| `chargingSessions[].sessionId`        | Number | 会话 ID                   |

---

## 会话管理

### GET /admin/sessions — 查看所有用户会话

**功能**：管理员分页查看所有用户的充电会话，支持按状态、充电桩和用户筛选。

```
GET /api/v1/admin/sessions?page=1&pageSize=20&status=charging&stationId=1&userId=1
Authorization: Bearer <admin_token>
```

**查询参数**：

| 参数          | 类型   | 必填 | 说明                                                                    |
| ------------- | ------ | ---- | ----------------------------------------------------------------------- |
| `page`      | Number | 否   | 页码，默认 1                                                            |
| `pageSize`  | Number | 否   | 每页数量，默认 20                                                       |
| `status`    | String | 否   | `queued` / `waiting` / `charging` / `completed` / `cancelled` |
| `stationId` | Number | 否   | 充电桩 ID                                                               |
| `userId`    | Number | 否   | 用户 ID                                                                 |

**响应字段**：

| 字段                          | 类型   | 说明       |
| ----------------------------- | ------ | ---------- |
| `list`                      | Array  | 会话列表   |
| `list[].sessionId`          | Number | 会话 ID    |
| `list[].status`             | String | 会话状态   |
| `list[].user`               | Object | 用户摘要   |
| `list[].user.id`            | Number | 用户 ID    |
| `list[].user.licensePlate`  | String | 车牌号     |
| `list[].station`            | Object | 充电桩摘要 |
| `list[].station.id`         | Number | 充电桩 ID  |
| `list[].station.name`       | String | 充电桩名称 |
| `list[].requestedEnergyKwh` | Number | 目标充电量 |
| `list[].chargedEnergyKwh`   | Number | 已充电量   |
| `list[].progress`           | Number | 充电进度   |
| `list[].createdAt`          | String | 创建时间   |
| `page`                      | Number | 当前页码   |
| `pageSize`                  | Number | 每页数量   |
| `total`                     | Number | 总数量     |

### GET /admin/sessions/:id — 查看单个用户会话详情

**功能**：管理员查看任意用户会话详情。响应结构与 `GET /sessions/:id` 保持一致，并额外返回用户摘要。

```
GET /api/v1/admin/sessions/:id
Authorization: Bearer <admin_token>
```

**响应字段**：

| 字段                  | 类型   | 说明                     |
| --------------------- | ------ | ------------------------ |
| `user`              | Object | 用户摘要                 |
| `user.id`           | Number | 用户 ID                  |
| `user.licensePlate` | String | 车牌号                   |
| 其他字段              | -      | 同 `GET /sessions/:id` |

---

## 账单管理

### GET /admin/bills — 查看所有用户历史账单

**功能**：管理员分页查看所有用户历史账单，支持按用户、车牌、充电桩、支付状态和时间范围筛选。系统默认按 `createdAt` 倒序返回，最新账单在前。

```
GET /api/v1/admin/bills?page=1&pageSize=20&userId=1&licensePlate=京A12345&stationId=1&paymentStatus=paid&startDate=2026-01-01&endDate=2026-06-08
Authorization: Bearer <admin_token>
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | Number | 否 | 页码，默认 1 |
| `pageSize` | Number | 否 | 每页数量，默认 20 |
| `userId` | Number | 否 | 用户 ID |
| `licensePlate` | String | 否 | 车牌号 |
| `stationId` | Number | 否 | 充电桩 ID |
| `paymentStatus` | String | 否 | `unpaid` / `paid` |
| `startDate` | String | 否 | 开始日期 `yyyy-MM-dd` |
| `endDate` | String | 否 | 结束日期 `yyyy-MM-dd` |

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `list` | Array | 账单列表 |
| `list[].billId` | Number | 账单 ID |
| `list[].sessionId` | Number | 关联会话 ID |
| `list[].user` | Object | 用户摘要 |
| `list[].user.id` | Number | 用户 ID |
| `list[].user.licensePlate` | String | 车牌号 |
| `list[].station` | Object | 充电桩摘要 |
| `list[].station.id` | Number | 充电桩 ID |
| `list[].station.name` | String | 充电桩名称 |
| `list[].chargedEnergyKwh` | Number | 实际充电量 |
| `list[].totalFee` | Number | 总费用 |
| `list[].paymentStatus` | String | `unpaid` / `paid` |
| `list[].createdAt` | String | 创建时间 |
| `list[].paidAt` | String\|null | 支付时间 |
| `page` | Number | 当前页码 |
| `pageSize` | Number | 每页数量 |
| `total` | Number | 总数量 |

### GET /admin/bills/:id — 查看单张账单详情

**功能**：管理员查看任意用户的单张账单详情。响应结构与 `GET /bills/:id` 保持一致。

```
GET /api/v1/admin/bills/:id
Authorization: Bearer <admin_token>
```

**前置条件**：

| 条件 | 说明 |
|------|------|
| 系统 | 当前 token 角色为 `admin` |
| 系统 | 账单 ID 存在 |

**响应字段**：同 `GET /bills/:id`。

---

## 队列管理

### GET /admin/queues — 查看所有队列

```
GET /api/v1/admin/queues
Authorization: Bearer <admin_token>
```

**响应**：返回所有充电桩的三个区域队列详情。

---

### PUT /admin/queues/reorder — 拖拽修改队列位置

```
PUT /api/v1/admin/queues/reorder
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**请求字段**：

| 字段            | 类型   | 说明                    |
| --------------- | ------ | ----------------------- |
| `stationId`   | Number | 充电桩 ID               |
| `zone`        | String | `queue` / `waiting` |
| `sessionId`   | Number | 要移动的会话 ID         |
| `newPosition` | Number | 目标位置（从 1 开始）   |

---

### PUT /admin/queues/move — 拖拽移动到其他桩

```
PUT /api/v1/admin/queues/move
Authorization: Bearer <admin_token>
```

**请求字段**：

| 字段                | 类型   | 说明                    |
| ------------------- | ------ | ----------------------- |
| `sessionId`       | Number | 会话 ID                 |
| `targetStationId` | Number | 目标充电桩 ID           |
| `targetZone`      | String | `queue`               |
| `targetPosition`  | Number | 目标位置（-1 表示队尾） |

---

## 报表

### GET /admin/reports/charging-volume — 充电量统计

```
GET /api/v1/admin/reports/charging-volume?startDate=2026-01-01&endDate=2026-06-08&granularity=month
Authorization: Bearer <admin_token>
```

**查询参数**：

| 参数            | 类型   | 必填 | 说明                                     |
| --------------- | ------ | ---- | ---------------------------------------- |
| `startDate`   | String | 是   | 开始日期 `yyyy-MM-dd`                  |
| `endDate`     | String | 是   | 结束日期                                 |
| `granularity` | String | 是   | 聚合粒度：`day` / `week` / `month` |

**响应字段**：

| 字段                       | 类型   | 说明                     |
| -------------------------- | ------ | ------------------------ |
| `totalEnergyKwh`         | Number | 总充电量                 |
| `totalSessions`          | Number | 总充电次数               |
| `dataPoints`             | Array  | 各周期数据点             |
| `dataPoints[].period`    | String | 周期标识（如 "2026-01"） |
| `dataPoints[].energyKwh` | Number | 该周期充电量             |
| `dataPoints[].sessions`  | Number | 该周期充电次数           |

---

### GET /admin/reports/revenue — 收入统计

```
GET /api/v1/admin/reports/revenue?startDate=2026-01-01&endDate=2026-06-08&granularity=month
Authorization: Bearer <admin_token>
```

**响应字段**：

| 字段                         | 类型   | 说明         |
| ---------------------------- | ------ | ------------ |
| `totalRevenue`             | Number | 总收入       |
| `electricityRevenue`       | Number | 电费收入     |
| `serviceRevenue`           | Number | 服务费收入   |
| `dataPoints`               | Array  | 各周期数据   |
| `dataPoints[].period`      | String | 周期         |
| `dataPoints[].revenue`     | Number | 该周期收入   |
| `dataPoints[].electricity` | Number | 该周期电费   |
| `dataPoints[].service`     | Number | 该周期服务费 |

---

### GET /admin/reports/utilization — 充电桩利用率

```
GET /api/v1/admin/reports/utilization?startDate=2026-01-01&endDate=2026-06-08
Authorization: Bearer <admin_token>
```

**响应字段**：

| 字段                               | 类型   | 说明               |
| ---------------------------------- | ------ | ------------------ |
| `overallUtilization`             | Number | 总体利用率（0~1）  |
| `stations`                       | Array  | 各桩利用率         |
| `stations[].stationId`           | Number | 桩 ID              |
| `stations[].stationName`         | String | 桩名称             |
| `stations[].utilization`         | Number | 该桩利用率         |
| `stations[].totalChargingHours`  | Number | 总充电时长（小时） |
| `stations[].totalAvailableHours` | Number | 总可用时长（小时） |

---

> 文档版本：v1.0 | 最后更新：2026-06-08
>
> 本文档覆盖所有用户端和管理端 API 接口，包含完整的请求/响应格式、字段说明、操作契约和多场景示例。
