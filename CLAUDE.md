# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**智能充电桩调度计费系统** — A university software engineering course project (第二次作业). The system manages EV charging station operations: user registration/authentication, charging dispatch with configurable strategies, three-zone queue management, tiered billing (time-of-use pricing + service fee), fault handling with five dispatch strategies, admin monitoring, and comprehensive system logging.

**Status**: Design phase (data design & architecture complete, code implementation not yet started).

**Tech Stack** (selected):
- Backend: Python (FastAPI)
- Database: SQLite (via SQLAlchemy ORM)
- Auth: JWT Token (python-jose)
- Scheduling: APScheduler
- Config: application.yml (PyYAML)
- Logging: Custom Logger (unified DB + terminal, 5 levels)

## Document Architecture

All design documents are in `docs/`. The key documents form a layered reference:

```
config/
├── application.yml                  # 系统配置文件 — 充电桩参数、策略、计费规则、日志阈值

docs/
├── 背景调研.md                       # Industry background & requirements research
├── 课程说明.md                       # Course assignment requirements (original)
├── 核心业务介绍.md                   # Core business description & 20 FRs
├── 用例模型.md                       # Use case diagram, SSDs, operation contracts, instruction table
├── UML流程图.md                      # Domain model class diagram, use-case-level class diagrams, activity diagram
├── 第二次作业-系统架构与分工.md        # Architecture decisions, personnel assignment, workload
├── 系统架构设计文档.md               # Implementation reference — tech stack, APIs, data models, flows, Logger
├── 数据设计说明.md                   # Database schema (13 tables), config design, Logger module design
└── 云平台文件/                       # Course reference materials (templates, slides)

src/                                  # Python 源码包
├── main.py                           # FastAPI 入口
├── config/                           # 配置加载
├── db/                               # 数据库 ORM 模型
├── enums/                            # Python 枚举定义
├── schemas/                          # Pydantic 请求/响应模型
├── services/                         # 领域服务
├── routers/                          # REST API 路由
└── utils/                            # 工具（Logger 等）

tests/                                # pytest 测试
requirements.txt                      # Python 依赖
```

> **Key reference for implementation**: Start with `docs/数据设计说明.md` for DB schema, then `docs/系统架构设计文档.md` for API and business logic.

## Database Schema (13 tables)

All tables are defined in `docs/数据设计说明.md` (including full SQLite DDL). Summary:

| # | Table | Purpose | Key Columns |
|---|-------|---------|-------------|
| 1 | `users` | 用户账号 | user_id, license_plate, password_hash, membership_level |
| 2 | `vehicles` | 车辆信息 | vehicle_id, user_id, battery_capacity_kwh, charging_protocol |
| 3 | `charging_piles` | 充电桩运行时状态 | pile_id, status, total_charge_num/time/capacity |
| 4 | `pile_protocols` | 桩↔协议多对多 | pile_id, protocol |
| 5 | `pile_tariff_configs` | 桩级独立计费规则 | pile_id, peak/normal/valley_price, service_fee config |
| 6 | `charging_requests` | 充电请求 + 三区队列 | request_id, car_id, pile_id, request_status, zone_type |
| 7 | `charging_sessions` | 充电会话 | session_id, start/end_time, charged_power_kwh |
| 8 | `billing_records` | 账单概览 | bill_id, total_charge_fee/service_fee/total_fee |
| 9 | `detailed_bills` | 分时段详单 | bill_id, period_name, charge_fee, service_fee |
| 10 | `payment_orders` | 支付订单 | order_id, bill_id, payment_status |
| 11 | `fault_events` | 故障事件 | event_id, pile_id, fault_type, handling_status |
| 12 | `system_logs` | **系统日志（统一日志表）** | log_id, module, level(0-4), detail |
| 13 | `dispatch_strategy_logs` | 策略变更历史 | operator, change_type, from_value, to_value |

### Configuration-vs-Database principle
- **Static/Env params** → `config/application.yml` (pile hardware params, capacity limits, time periods, default prices, log threshold)
- **Dynamic/Business data** → SQLite DB (user accounts, vehicle data, requests, sessions, bills, logs)

## Logging System

Designed in detail at `docs/数据设计说明.md §七`. Key design:

### 5 Log Levels
| Value | Name | Typical Usage |
|-------|------|---------------|
| 0 | INFO (常规) | Normal operations: login, charging start/end, bill generation |
| 1 | NOTICE (注意) | Configuration changes: strategy switch, admin operations |
| 2 | WARN (警告) | Recoverable issues: queue full, protocol mismatch |
| 3 | ERROR (严重) | Service impairment: pile fault, billing error |
| 4 | CRITICAL (崩溃) | System cannot continue: DB connection lost |

### 10 Modules
SYSTEM, ACCOUNT, DISPATCH, QUEUE, BILLING, MONITOR, ADMIN, FAULT, SCHEDULER, API

### Logging Behavior
- **All logs** are written to `system_logs` table in DB
- **Logs at/above** `logging.console_threshold` (in application.yml) are also printed to terminal
- Default threshold: `1` (NOTICE and above → terminal, INFO level → DB only)

### Logger API (reference for implementation)
```python
logger = Logger(db_session, config)
logger.info(module, detail)      # always to DB, NOTICE+ also to terminal
logger.notice(module, detail)
logger.warn(module, detail)
logger.error(module, detail)
logger.critical(module, detail)
```

## Key Design Decisions

### Architecture: Layered (4 tiers)
- L1 表示层 (Presentation) — Client apps (user web/mini-program + admin dashboard)
- L2 应用层 (Application) — Router + ScheduledTaskService
- L3 领域层 (Domain) — DispatchService, QueueService, BillingService, MonitorService, AccountService, DispatchStrategy
- L4 基础设施层 (Infrastructure) — SQLite database, application.yml config, **Logger**

**Layer rules**:
- Presentation only talks to Application via REST
- Application calls Domain services for business logic
- Domain services use Infrastructure for persistence and logging
- Cross-layer calls and reverse dependencies prohibited
- **Exception**: All layers may depend on Logger (infrastructure capability, not a business dependency)

### Communication: RESTful API
- All 18 system instructions map to REST endpoints (see `docs/系统架构设计文档.md §5`)
- Status polling: Admin client polls `GET /api/piles/{pile_Id}/state` periodically

### Three-Zone Queue Model (Per-Pile)
Each charging pile independently maintains three zones:
- 排队区 (Queue area) — vehicles can freely switch to other piles' queues
- 等待区 (Waiting area) — vehicles cannot switch queues; can exit with 0 fee
- 充电区 (Charging area) — actively charging

### Dispatch Strategies (Configurable)
- **Normal allocation**: SHORTEST_TOTAL_TIME (default, greedy) or BATCH_SHORTEST_TIME (Hungarian algorithm)
- **Fault handling**: PRIORITY, TIME_ORDER, FAULT_RECOVERY, SHORTEST_TOTAL_TIME, BATCH_SHORTEST_TIME
- **Switching**: Startup parameter (application.yml) + admin runtime switch via API

### Scheduling Algorithm

**Single (greedy)** — per-vehicle: Tᵢ = wᵢ(wait) + cᵢ(charge), pick min(Tᵢ)
**Batch (Hungarian)** — N×M cost matrix, optimal assignment in O(N³)

### Billing
```
Total = electricity fee + service fee
Electricity = Σ(charge per time-slot × corresponding price)
Service fee = baseFee + timeCoefficient × duration
```

## Diagram Conventions

All diagrams use Mermaid syntax:
- `classDiagram` — domain model and use-case-level class diagrams
- `sequenceDiagram` — system sequence diagrams (SSD) and fault interaction diagrams
- `flowchart TD/LR` — activity diagrams, architecture topology, queue model
- Class relationships are restricted to: `-->` (directed association), `..>` (dependency), `<|--` (inheritance)

## Development Notes

- **Starting point**: Implement `Logger` and database initialization first (Phase 1 in 系统架构设计文档 §11.1)
- **Data design reference**: Always consult `docs/数据设计说明.md` for exact column names, types, and constraints before writing SQLAlchemy models
- **Logging everywhere**: Insert `logger.info(module, detail)` at every key operation point (see the 40+ logging points table in 数据设计说明.md §7.3)
- **Config first**: Read `config/application.yml` at startup via `ConfigLoader`, expose to all services
- When adding new features, ensure corresponding SSD + operation contract + instruction table entries are added to `docs/用例模型.md`
- Class diagram modifications must only use the three allowed relationship types
- All 用例编号 use UC-XX format; sequence numbers are sequential
- All 契约编号 use sequential numbering (currently 27 contracts)
- Document language: Chinese (documentation) with English (code identifiers/REST paths)
