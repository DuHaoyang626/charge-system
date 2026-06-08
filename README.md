# 智能充电桩调度计费系统

> EV Charging Station Dispatch & Billing System — 大学软件工程课程项目

基于 **FastAPI + SQLite** 的电动汽车充电站管理系统，提供用户注册认证、充电调度（三区队列）、分时计费、故障处理、管理员监控等全流程服务。

---

## 目录

- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 文档](#api-文档)
- [项目结构](#项目结构)
- [核心设计](#核心设计)

---

## 技术栈

| 层面 | 技术 | 说明 |
|------|------|------|
| Web 框架 | [FastAPI](https://fastapi.tiangolo.com/) | 高性能异步框架，自动生成 OpenAPI 文档 |
| 数据库 | SQLite + [SQLAlchemy 2.0](https://www.sqlalchemy.org/) | ORM 方式操作，开箱即用无需额外安装数据库 |
| 认证 | python-jose (JWT) + passlib (bcrypt) | Token 认证 |
| 定时任务 | APScheduler | 调度策略定时触发 |
| 配置 | PyYAML + Pydantic | `config/application.yml` → 类型安全对象 |
| 日志 | 自研 Logger | 统一 DB 存储 + 终端输出，5 级日志 10 个模块 |

---

## 快速开始

### 环境要求

- Python **3.10+**
- pip

### 1. 克隆项目

```bash
git clone <repo-url>
cd charge-system
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 初始化数据库

项目启动时会**自动完成**以下初始化动作，无需手动执行 SQL：

1. 读取 `config/application.yml` 加载系统配置
2. 在 `data/` 目录下自动创建 SQLite 数据库文件 `charge_system.db`
3. 自动创建全部 **13 张数据库表**（users, vehicles, charging_piles, ...）
4. 将 `application.yml` 中配置的充电桩同步注册到数据库
5. 加载默认调度策略

> 如果需要重新初始化，删除 `data/charge_system.db` 文件后重启即可。

### 4. 启动后端服务

```bash
# 标准启动（开发模式，热重载）
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 生产启动
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 5. 验证服务

启动后访问以下地址：

- **API 根路径**：http://localhost:8000/ — 返回 `{"message": "智能充电桩调度计费系统 API", "version": "0.1.0"}`
- **Swagger 文档**：http://localhost:8000/docs — 交互式 API 调试界面
- **ReDoc 文档**：http://localhost:8000/redoc — 备选 API 文档

---

## 配置说明

系统配置文件位于 `config/application.yml`，包含以下主要配置项：

```yaml
# 充电桩定义（新增桩只需在此添加，重启自动识别）
piles:
  - id: "P001"
    name: "快充桩-01"
    type: fast_charge
    max_power_kw: 120.0
    protocols: [GB_STANDARD, CCS]
    parking_spots: 2

# 调度策略（启动默认，运行中可通过 API 切换）
dispatch:
  default_algorithm: "SHORTEST_TOTAL_TIME"       # 或 BATCH_SHORTEST_TIME
  default_fault_strategy: "TIME_ORDER"

# 计费规则
billing:
  time_periods:            # 峰/平/谷时段定义
    peak:                  # 峰时 10:00-12:00, 17:00-19:00
    valley:                # 谷时 00:00-08:00, 22:00-23:59
    normal:                # 平时为剩余时段
  default_prices:
    peak_price: 1.2        # 峰时电价（元/kWh）
    normal_price: 0.8
    valley_price: 0.4
  service_fee:
    base_fee: 5.0          # 基础服务费（元）
    time_coefficient: 0.5  # 时长系数（元/分钟）

# 日志
logging:
  console_threshold: 1     # 终端日志阈值（0=常规, 1=注意, 2=警告, 3=严重, 4=崩溃）
                            # -1 = 仅写 DB，不输出终端

# 系统
system:
  db_path: "data/charge_system.db"
  jwt_secret: "charge-system-jwt-secret-key-2026"
  token_expire_minutes: 1440
```

> **配置与数据分离原则**：桩硬件参数、时段定义、默认电价等静态配置在 `application.yml` 中；用户账号、充电记录、账单等运行时数据存储在 SQLite 数据库中。

---

## API 文档

### 用户端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/accounts` | 创建新账号（车牌号、用户名、电池容量） |
| PUT | `/api/accounts/{car_id}/password` | 设置/修改密码 |
| POST | `/api/auth/login` | 登录（返回 JWT Token） |
| POST | `/api/charging/requests` | 提交充电申请 |
| PUT | `/api/charging/requests/{car_id}/amount` | 修改充电电量 |
| PUT | `/api/charging/requests/{car_id}/mode` | 修改充电模式 |
| GET | `/api/charging/requests/{car_id}/state` | 查询排队状态 |
| POST | `/api/charging/sessions` | 开始充电 |
| GET | `/api/charging/sessions/{car_id}` | 查询充电状态（含模拟实时数据） |
| DELETE | `/api/charging/sessions/{car_id}` | 结束充电（自动生成账单） |
| GET | `/api/bills?car_id=&date=` | 查看账单历史 |
| GET | `/api/bills/{bill_id}/details` | 查看分时段详单 |
| POST | `/api/payments/{bill_id}/pay` | 支付账单（模拟） |

### 管理员端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/piles/{pile_id}/power/on` | 启动充电桩电源 |
| PUT | `/api/piles/{pile_id}/parameters` | 设置充电桩计费参数 |
| POST | `/api/piles/{pile_id}/run` | 运行充电桩 |
| POST | `/api/piles/{pile_id}/power/off` | 关闭充电桩 |
| GET | `/api/piles/{pile_id}/state` | 查看充电桩状态 |
| GET | `/api/queues/state?queuelist=P001,P002` | 查看指定桩队列状态（三区车辆明细） |
| GET | `/api/strategies` | 获取当前调度策略 |
| PUT | `/api/strategies/dispatch` | 切换分配策略（运行时） |
| PUT | `/api/strategies/fault` | 切换故障策略（运行时） |
| PUT | `/api/admin/vehicles/{car_id}/move` | 移动车辆位置（管理员手动调整） |
| GET | `/api/admin/reports` | 生成运营报表 |

> 完整的请求/响应示例请参阅启动后的 Swagger 文档：http://localhost:8000/docs

---

## 项目结构

```
charge-system/
├── config/
│   └── application.yml           # 系统配置文件（充电桩、策略、计费、日志）
├── data/
│   └── charge_system.db          # SQLite 数据库文件（启动后自动生成）
├── docs/                         # 课程设计文档
│   ├── 背景调研.md                # 行业背景与需求调研
│   ├── 核心业务介绍.md             # 核心业务与 20 项功能需求
│   ├── 用例模型.md                # 用例图、SSD、契约
│   ├── UML流程图.md               # 领域模型类图、活动图
│   ├── 数据设计说明.md             # 数据库 DDL、日志系统设计
│   └── 系统架构设计文档.md          # 架构决策、API 定义、数据流
├── src/
│   ├── main.py                   # FastAPI 应用入口（生命周期管理）
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py             # ConfigLoader — 读取 application.yml
│   │   └── settings.py           # Pydantic 配置模型
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py           # 数据库连接与会话管理
│   │   └── models.py             # SQLAlchemy ORM 模型（全部 13 张表）
│   ├── enums/
│   │   └── __init__.py           # 枚举定义（ChargeMode, PileStatus, ZoneType 等）
│   ├── schemas/
│   │   ├── __init__.py           # Pydantic 基类
│   │   ├── user.py               # 注册/登录请求响应
│   │   ├── charging.py           # 充电/队列请求响应
│   │   ├── billing.py            # 账单/详单响应
│   │   └── admin.py             # 桩管理/策略请求响应
│   ├── routers/
│   │   ├── account.py            # POST /api/accounts
│   │   ├── auth.py               # POST /api/auth/login
│   │   ├── charging.py           # 充电全流程
│   │   ├── bills.py              # 账单查询
│   │   ├── piles.py              # 充电桩管理
│   │   ├── queues.py             # 队列状态查询
│   │   ├── strategies.py         # 策略管理
│   │   ├── payments.py           # 支付
│   │   └── admin.py              # 管理员功能
│   ├── services/
│   │   ├── account_service.py    # 账号服务
│   │   ├── dispatch_service.py   # 调度服务
│   │   ├── dispatch_strategy.py  # 调度策略管理
│   │   ├── queue_service.py      # 队列服务
│   │   ├── billing_service.py    # 计费服务
│   │   ├── monitor_service.py    # 监控服务
│   │   └── payment_service.py    # 支付服务
│   └── utils/
│       └── logger.py             # 统一日志服务（DB + 终端）
└── requirements.txt              # Python 依赖清单
```

---

## 核心设计

### 三区队列模型

每个充电桩独立维护三个区域：

```
排队区 (QUEUE_AREA)   →   等待区 (WAITING_AREA)   →   充电区 (CHARGING_AREA)
   可自由换桩              不可换桩，退出扣费             正在充电
   容量：无上限              容量：5 辆                      容量：2 辆
```

### 调度策略

- **正常分配**：`SHORTEST_TOTAL_TIME`（贪心，默认） / `BATCH_SHORTEST_TIME`（匈牙利算法）
- **故障处理**：PRIORITY / TIME_ORDER / FAULT_RECOVERY / SHORTEST_TOTAL_TIME / BATCH_SHORTEST_TIME
- **运行时切换**：通过 API 动态切换，不影响进行中的会话

### 计费规则

```
总费用 = 电费 + 服务费
电费   = Σ(各时段充电量 × 对应时段电价)     # 峰/平/谷三段
服务费 = 基础服务费 + 时长系数 × 充电时长
```

### 日志系统

- 全部日志写入 `system_logs` 表（DB）
- 等级 ≥ `console_threshold` 的同时输出到终端
- 10 个日志模块：SYSTEM, ACCOUNT, DISPATCH, QUEUE, BILLING, MONITOR, ADMIN, FAULT, SCHEDULER, API

---

## 开发参考

- **数据库表结构**：详见 `docs/数据设计说明.md`（13 张表完整 DDL）
- **API 详细定义**：详见 `docs/系统架构设计文档.md §五`
- **用例与契约**：详见 `docs/用例模型.md`
- **启动生命周期**：`src/main.py` 中的 `lifespan` 函数定义了完整的 7 步启动流程
