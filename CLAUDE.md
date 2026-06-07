# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**智能充电桩调度计费系统** — A university software engineering course project (第二次作业). The system manages EV charging station operations: user registration/authentication, charging dispatch with configurable strategies, three-zone queue management, tiered billing (time-of-use pricing + service fee), fault handling with five dispatch strategies, and admin monitoring.

**Status**: Design phase (documentation complete, code implementation not yet started).

**Tech Stack** (selected):
- Backend: Python (FastAPI)
- Database: SQLite (via SQLAlchemy ORM)
- Auth: JWT Token (python-jose)
- Scheduling: APScheduler
- Config: application.yml (PyYAML)

## Document Architecture

All design documents are in `docs/`. The key documents form a layered reference:

```
docs/
├── 背景调研.md                    # Industry background & requirements research
├── 课程说明.md                    # Course assignment requirements (original)
├── 核心业务介绍.md                # Core business description & 20 FRs
├── 用例模型.md                    # Use case diagram, SSDs, operation contracts, instruction table
├── UML流程图.md                   # Domain model class diagram, use-case-level class diagrams, activity diagram
├── 第二次作业-系统架构与分工.md    # Architecture decisions, personnel assignment, workload
├── 系统架构设计文档.md            # Implementation reference — tech stack, APIs, data models, flows
└── 云平台文件/                     # Course reference materials (templates, slides)
```

## Key Design Decisions

### Architecture: Layered (4 tiers)
- L1 表示层 (Presentation) — Client apps (user web/mini-program + admin dashboard)
- L2 应用层 (Application) — Router + ScheduledTaskService
- L3 领域层 (Domain) — DispatchService, QueueService, BillingService, MonitorService, AccountService, DispatchStrategy
- L4 基础设施层 (Infrastructure) — SQLite database, application.yml config

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

- When adding new features, ensure corresponding SSD + operation contract + instruction table entries are added to `docs/用例模型.md`
- Class diagram modifications must only use the three allowed relationship types
- All 用例编号 use UC-XX format; sequence numbers are sequential
- All 契约编号 use sequential numbering (currently 27 contracts)
- Document language: Chinese (documentation) with English (code identifiers/REST paths)
