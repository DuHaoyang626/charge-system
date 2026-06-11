# 开发阶段安排

> 本文档将整个系统拆分为多个独立开发阶段，每个阶段可独立完成、验证。
> 后端和前端各自独立启动，前端可通过配置文件指定后端地址和端口。

---

## 开发环境说明

### 后端启动

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Swagger 文档：`http://127.0.0.1:8000/docs`

### 前端启动

```bash
cd frontend
npm run dev -- --port 5173
```

### 前后端连接

前端通过 `.env` 或配置文件指定后端地址：

```env
# frontend/.env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

前端所有 API 调用均基于此地址，切换后端只需修改此变量。

---

## 各阶段一览

| 阶段 | 名称 | 产出 API 数 | 预计工时 |
|------|------|-------------|----------|
| 0 | 项目脚手架 + 基础设施 | 0（骨架） | 1h |
| 1 | 认证模块（注册/登录/鉴权） | 3 | 2h |
| 2 | 充电协议与充电桩管理 | 6 | 2h |
| 3 | 充电会话·排队阶段 | 4 | 2h |
| 4 | 自动调度循环 | 0（后台） + 2 | 3h |
| 5 | 充电会话·充电阶段 | 5 | 3h |
| 6 | 账单与支付 | 4 | 2h |
| 7 | 管理端·队列管理与调度 | 4 | 2h |
| 8 | 管理端·配置与报表 | 7 | 2h |
| 9 | 前端接入与联调 | — | 按需 |
| 10 | 补丁与优化 | — | 按需 |

---

## 阶段 0：项目脚手架 + 基础设施

### 目标

搭建后端工程骨架，基础设施可运行，数据库可初始化，Swagger 可访问。

### 前置条件

- Python ≥ 3.11 已安装
- 设计文档 `docs/design/` 就绪

### 给 Claude Code 的提示词

```
你是一个 Python 后端开发者。请根据以下设计文档搭建 FastAPI 项目骨架。

设计文档路径：
- docs/design/02-技术选型.md（技术栈 + 项目结构）
- docs/design/04-编码前设计决策.md（异常处理、配置、时区、deps、调度循环、种子数据）

要求：
1. 创建 backend/ 目录及所有子目录（api/*、service/*、model/*、core/*、scheduler/）
2. 创建 pyproject.toml，依赖包括：fastapi, uvicorn[standard], sqlmodel, python-jose[cryptography], passlib[bcrypt], python-multipart
3. 创建 core/config.py（读取 .env 中的 JWT_SECRET_KEY 和 DATABASE_URL）
4. 创建 core/database.py（engine + init_db + 种子数据函数）
5. 创建 core/security.py（create_access_token + verify_token + password hash）
6. 创建 core/exceptions.py（AppException + Err 错误码枚举）
7. 创建 core/exception_handlers.py（全局异常处理器）
8. 创建 core/deps.py（get_current_user, get_current_admin, get_db, get_pagination）
9. 创建 model/ 下的所有 SQLModel（user, station, protocol, session, bill, config, schedule_log）
10. 创建 main.py（lifespan 启动 init_db，注册全局异常处理器，包含全部路由引用占位）
11. 创建 scheduler/dispatch_loop.py（DispatchLoop 类的空壳，含 start/stop/tick 方法签名）
12. 根目录创建 .env 文件（JWT_SECRET_KEY 和 DATABASE_URL）
13. 运行后 uvicorn main:app --reload 可启动，访问 /docs 显示 Swagger 页面
```

### 预期可检查状况

| 检查项 | 方法 |
|--------|------|
| 项目结构完整 | 目录树匹配 02-技术选型.md |
| `uvicorn main:app --reload` 启动 | 终端无报错 |
| `http://127.0.0.1:8000/docs` 可访问 | 浏览器打开显示 Swagger |
| 数据库初始化 | `data/charge_system.db` 文件生成 |
| 种子数据写入 | 数据库中存在 protocols 5 条、stations 2 条、admin 账号 |

### 自动化测试脚本

```python
# backend/tests/test_stage0_infrastructure.py
"""
阶段 0 验证：项目可启动、数据库可初始化、种子数据正确。
运行：pytest tests/test_stage0_infrastructure.py -v
"""

def test_project_imports():
    """所有核心模块可导入"""
    from core.config import settings
    from core.database import engine, init_db
    from core.security import create_access_token, verify_token, get_password_hash
    from core.exceptions import AppException, Err
    from core.deps import get_current_user, get_current_admin
    from model.user import User
    from model.station import Station
    from model.protocol import Protocol
    from model.session import ChargingSession
    from model.bill import Bill
    from model.config import GlobalConfig, ElectricityPrice, ServiceFeeTier
    from scheduler.dispatch_loop import DispatchLoop
    assert True


def test_seed_data():
    """种子数据正确写入"""
    from sqlmodel import Session, select
    from core.database import engine
    from model.protocol import Protocol
    from model.station import Station
    from model.user import User

    with Session(engine) as db:
        protocols = db.exec(select(Protocol)).all()
        assert len(protocols) >= 5, f"协议数量不足: {len(protocols)}"

        stations = db.exec(select(Station)).all()
        assert len(stations) >= 2, f"充电桩数量不足: {len(stations)}"

        admin = db.exec(select(User).where(User.license_plate == "ADMIN")).first()
        assert admin is not None, "管理员账号未创建"
        assert admin.role == "admin"


def test_jwt_roundtrip():
    """JWT 签发与验签正常"""
    from core.security import create_access_token, verify_token

    token = create_access_token(user_id=1, role="user")
    payload = verify_token(token)
    assert payload is not None
    assert payload["user_id"] == 1
    assert payload["role"] == "user"


def test_password_hash():
    """密码哈希与校验正常"""
    from core.security import get_password_hash, verify_password

    hashed = get_password_hash("test123")
    assert verify_password("test123", hashed)
    assert not verify_password("wrong", hashed)
```

### 前端人工检查

| 操作 | 预期结果 |
|------|----------|
| 浏览器打开 `http://127.0.0.1:8000/docs` | 显示 Swagger 页面，标题为"智能充电桩调度计费系统" |
| 展开任意一个占位路由（如 GET /stations） | 可看到接口定义（即使尚未实现） |

---

## 阶段 1：认证模块

### 目标

实现用户注册、登录、获取当前用户信息，JWT Token 可正确签发和验证。
目标：可以完成 **注册 → 登录 → 用 Token 访问需要鉴权的接口** 的全流程。

### 前置条件

阶段 0 完成并可运行。

### 给 Claude Code 的提示词

```
请实现认证相关的 API 接口。参照 docs/design/01-API接口说明.md 中的认证模块部分。
参考 docs/design/04-编码前设计决策.md 中的错误码、deps、异常处理。

需要实现：
1. api/auth/ 模块：
   - api/auth/__init__.py
   - api/auth/router.py（路由定义）
   - api/auth/schema.py（请求/响应 Pydantic 模型）

2. 三个接口：
   A. POST /api/v1/auth/register
      - 接收 licensePlate, userName, batteryCapacity, password, confirmPassword, protocolIds
      - 校验 password === confirmPassword
      - 校验 licensePlate 唯一
      - 创建 User，密码 bcrypt 哈希
      - 返回 userId, licensePlate, userName, token

   B. POST /api/v1/auth/login
      - 接收 licensePlate, password
      - 校验账号密码
      - 返回 userId, licensePlate, userName, token, role

   C. GET /api/v1/users/me
      - 从 JWT 提取 userId
      - 返回完整用户信息：userId, licensePlate, userName, phone, batteryCapacity, protocols, activeSession
      - activeSession：查询该用户是否有进行中的会话（queued/waiting/charging），有则返回摘要

3. service/account/ 模块：
   - service/account/__init__.py
   - service/account/service.py（注册、登录、获取用户信息的业务逻辑）

4. 注意点：
   - 注册时 protocolIds 必须在系统已存在的 protocol 范围内
   - 密码错误和账号不存在都返回相同错误信息（防撞库）
   - 注册成功后直接返回 token，无需再次登录
```

### 预期可检查状况

| 检查项 | 方法 |
|--------|------|
| 注册成功 | POST /auth/register 返回 201 + token |
| 重复注册失败 | 同一车牌号再次注册返回 400 "该车牌号已注册" |
| 登录成功 | POST /auth/login 返回 200 + token + role |
| 错误密码登录 | 返回 400 "账号或密码错误" |
| 用 Token 访问 /users/me | 返回完整用户信息 |
| 无 Token 访问 /users/me | 返回 401 |
| 注册后数据库有对应用户 | 查询 users 表存在该记录 |

### 自动化测试脚本

```python
# backend/tests/test_stage1_auth.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

REGISTER_DATA = {
    "licensePlate": "粤B12345",
    "userName": "测试车辆",
    "batteryCapacity": 60.0,
    "password": "test123456",
    "confirmPassword": "test123456",
    "protocolIds": [1, 3],
}


class TestRegister:
    def test_register_success(self):
        resp = client.post("/api/v1/auth/register", json=REGISTER_DATA)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "token" in data
        assert data["licensePlate"] == "粤B12345"
        assert data["userName"] == "测试车辆"

    def test_register_duplicate_plate(self):
        resp = client.post("/api/v1/auth/register", json=REGISTER_DATA)
        assert resp.status_code == 400
        assert "已注册" in resp.json()["message"]

    def test_register_password_mismatch(self):
        data = {**REGISTER_DATA, "licensePlate": "粤C67890", "confirmPassword": "different"}
        resp = client.post("/api/v1/auth/register", json=data)
        assert resp.status_code == 400

    def test_register_invalid_protocol(self):
        data = {**REGISTER_DATA, "licensePlate": "粤D67890", "protocolIds": [999]}
        resp = client.post("/api/v1/auth/register", json=data)
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self):
        resp = client.post("/api/v1/auth/login", json={
            "licensePlate": "粤B12345",
            "password": "test123456",
        })
        assert resp.status_code == 200
        assert "token" in resp.json()["data"]

    def test_login_wrong_password(self):
        resp = client.post("/api/v1/auth/login", json={
            "licensePlate": "粤B12345",
            "password": "wrongpassword",
        })
        assert resp.status_code == 400

    def test_login_nonexistent(self):
        resp = client.post("/api/v1/auth/login", json={
            "licensePlate": "京NONEXIST",
            "password": "test123456",
        })
        assert resp.status_code == 400


class TestUserMe:
    def _login(self):
        resp = client.post("/api/v1/auth/login", json={
            "licensePlate": "粤B12345",
            "password": "test123456",
        })
        return resp.json()["data"]["token"]

    def test_get_user_me_success(self):
        token = self._login()
        resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["licensePlate"] == "粤B12345"
        assert "batteryCapacity" in data
        assert "protocols" in data

    def test_get_user_me_no_token(self):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401

    def test_get_user_me_invalid_token(self):
        resp = client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401
```

### 前端人工检查

| 操作 | 预期结果 |
|------|----------|
| 注册页面填写信息并提交 | 返回成功，自动跳转到主页 |
| 使用已注册的车牌号再次注册 | 提示"该车牌号已注册" |
| 登录页面输入正确账号密码 | 成功登录，跳转主页 |
| 登录页面输入错误密码 | 提示"账号或密码错误" |
| 手动清除 token 后刷新页面 | 跳转回登录页 |

---

## 阶段 2：充电协议与充电桩管理

### 目标

实现充电桩和协议的查询接口（用户端），以及充电桩的增删改查接口（管理端）。
目标：用户可以看到充电桩列表和详情，管理员可以创建和配置充电桩。

### 前置条件

阶段 1 完成（需要登录 token 测试鉴权接口）。

### 给 Claude Code 的提示词

```
请实现充电桩和充电协议的查询与管理接口。

需要实现：

1. model/ 中 StationProtocol 关联表模型（如果阶段 0 未实现）

2. api/stations/ 模块（用户端）：
   - GET /api/v1/stations — 获取所有充电桩列表（含状态、各区域数量、支持的协议、预估等待时长）
   - GET /api/v1/stations/:id — 获取单个充电桩详情（含排队区/等待区/充电区车辆列表）

3. api/admin/stations/ 模块（管理端）：
   - POST /api/v1/admin/stations — 创建充电桩
   - PUT /api/v1/admin/stations/:id — 修改充电桩配置
   - DELETE /api/v1/admin/stations/:id — 删除充电桩（三个区域均无车辆时才能删除）
   - POST /api/v1/admin/stations/:id/start — 启动充电桩
   - POST /api/v1/admin/stations/:id/stop — 正常停止
   - POST /api/v1/admin/stations/:id/emergency-stop — 异常停止（先实现骨架，调度逻辑在阶段 7 完善）

4. service/station/service.py — 充电桩相关的业务逻辑

5. 注意：
   - 用户端接口需要登录（get_current_user）
   - 管理端接口需要管理员权限（get_current_admin）
   - 获取充电桩详情时，车辆列表中的车牌号可能需脱敏
   - 删除充电桩前检查三个区域 count 是否为 0
   - 正常停止：将 status 设为 stopping，队列清空后自动 stopped（调度循环处理）
```

### 预期可检查状况

| 检查项 | 方法 |
|--------|------|
| GET /stations 返回桩列表 | 返回 200，包含 A/B 两个演示桩 |
| GET /stations/:id 返回详情 | 返回 200，包含三个区域的车辆列表（初始为空） |
| 管理员创建充电桩 | POST /admin/stations 返回 201 |
| 普通用户创建充电桩 | 返回 403 禁止 |
| 删除有车辆的桩 | 返回 400 "充电桩仍有车辆" |
| 启动/停止充电桩 | 状态正确切换 |

### 自动化测试脚本

```python
# backend/tests/test_stage2_stations.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def user_token():
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "粤B12345",
        "password": "test123456",
    })
    return resp.json()["data"]["token"]

@pytest.fixture
def admin_token():
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "ADMIN",
        "password": "admin123",
    })
    return resp.json()["data"]["token"]


class TestUserStations:
    def test_list_stations(self, user_token):
        resp = client.get("/api/v1/stations", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["stations"]) >= 2
        for s in data["stations"]:
            assert "name" in s
            assert "status" in s
            assert "supportedProtocols" in s

    def test_station_detail(self, user_token):
        resp = client.get("/api/v1/stations/1", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == 1
        assert "queueList" in data
        assert "chargingList" in data

    def test_station_not_found(self, user_token):
        resp = client.get("/api/v1/stations/999", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 404


class TestAdminStations:
    def test_create_station(self, admin_token):
        resp = client.post("/api/v1/admin/stations",
            json={"name": "C区-03号桩", "queueCapacity": 5, "waitingCapacity": 3,
                  "chargingCapacity": 2, "protocolIds": [1, 3, 4]},
            headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in (200, 201)

    def test_create_station_forbidden(self, user_token):
        resp = client.post("/api/v1/admin/stations",
            json={"name": "D区-04号桩", "queueCapacity": 5, "waitingCapacity": 3,
                  "chargingCapacity": 2, "protocolIds": [1]},
            headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 403

    def test_start_stop_station(self, admin_token):
        # 停止
        resp = client.post("/api/v1/admin/stations/1/stop",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        # 启动
        resp = client.post("/api/v1/admin/stations/1/start",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
```

### 前端人工检查

| 操作 | 预期结果 |
|------|----------|
| 用户登录后查看主页 | 显示充电桩列表，各桩名称、状态、各区域容量条 |
| 点击某个充电桩 | 进入详情页，显示三个区域的车辆列表 |
| 管理员进入管理后台 | 可看到充电桩列表和"创建桩"按钮 |
| 管理员创建一个新充电桩 | 新桩出现在列表中 |
| 管理员点击"删除"有车辆的桩 | 提示"仍有车辆，无法删除" |

---

## 阶段 3：充电会话·排队阶段

### 目标

实现用户发起充电请求 → 进入排队区 → 查看排队状态 → 换队 → 取消的全流程。
这是用户充电流程的第一段，到排队为止。

### 前置条件

阶段 1（认证）+ 阶段 2（充电桩）完成。

### 给 Claude Code 的提示词

```
请实现充电会话的排队阶段功能。

需要实现：

1. api/sessions/ 模块：
   - POST /api/v1/sessions — 发起充电请求
     * 接收 requestedEnergyKwh, protocolIds
     * 用户身份从 JWT 提取
     * DispatchService 自动计算最佳充电桩
     * 将用户加入排队区队尾
     * 返回 sessionId, status="queued", zone="queue", queuePosition, station
   
   - GET /api/v1/sessions/:id — 获取会话详情
     * 返回完整会话信息（含 currentFee 字段）
     * 所有状态（queued/waiting/charging/completed/cancelled）都正确处理
     * 校验会话属于当前用户
   
   - GET /api/v1/sessions/:id/switch-options — 获取可换入充电桩
     * 返回当前排队区可换入的 running 状态充电桩列表
   
   - POST /api/v1/sessions/:id/switch-station — 换到其他桩排队
     * 校验当前状态为 queued
     * 校验目标桩为 running 且排队区有空位
     * 更新会话的 station_id 和 queue_position
   
   - POST /api/v1/sessions/:id/cancel — 取消充电
     * queued 态取消：免费，status = cancelled
     * waiting 态取消：收基础服务费，生成 bill

2. service/dispatch/ 模块：
   - DispatchService.findBestStation(userId, protocolIds) — 计算最佳充电桩
     * 筛选 running 状态且排队区未满的桩
     * 筛选兼容用户协议的桩
     * 按排队人数升序排列，选排队最短的

3. service/queue/ 模块：
   - QueueService.enqueue(session, station) — 加入排队区，分配 queue_position
   - QueueService.moveToStation(session, targetStation) — 换队
   - QueueService.cancel(session) — 取消

4. 参考 docs/design/01-API接口说明.md 中 第三部分 充电会话模块 的前半部分（POST /sessions, GET /sessions/:id, switch-options, switch-station, cancel）
```

### 预期可检查状况

| 检查项 | 方法 |
|--------|------|
| 发起充电请求成功 | POST /sessions 返回 201，status=queued |
| 排队位置正确 | 连续创建 3 个会话，位置分别为 1, 2, 3 |
| 排队区满时发起失败 | 演示桩容量只有 5，第 6 个返回 400 |
| 同一用户重复发起 | 返回 409 "已有进行中的会话" |
| 获取会话详情 | GET /sessions/:id 返回完整信息 |
| 换队成功 | switch-station 后 station_id 改变 |
| 排队区取消免费 | cancel 返回 status=cancelled，无 bill |
| 查看不属于自己的会话 | 返回 403 |

### 自动化测试脚本

```python
# backend/tests/test_stage3_session_queue.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def user_a_token():
    # 注册并登录用户 A
    resp = client.post("/api/v1/auth/register", json={
        "licensePlate": "测试排队A", "userName": "用户A", "batteryCapacity": 60,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 3],
    })
    if resp.status_code == 201:
        return resp.json()["data"]["token"]
    resp = client.post("/api/v1/auth/login", json={"licensePlate": "测试排队A", "password": "test123"})
    return resp.json()["data"]["token"]

@pytest.fixture
def user_b_token():
    resp = client.post("/api/v1/auth/register", json={
        "licensePlate": "测试排队B", "userName": "用户B", "batteryCapacity": 60,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 3],
    })
    if resp.status_code == 201:
        return resp.json()["data"]["token"]
    resp = client.post("/api/v1/auth/login", json={"licensePlate": "测试排队B", "password": "test123"})
    return resp.json()["data"]["token"]


class TestCreateSession:
    def test_create_session_success(self, user_a_token):
        resp = client.post("/api/v1/sessions",
            json={"requestedEnergyKwh": 30.0, "protocolIds": [1, 3]},
            headers={"Authorization": f"Bearer {user_a_token}"})
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "queued"
        assert data["zone"] == "queue"
        assert data["queuePosition"] >= 1

    def test_duplicate_session_fails(self, user_a_token):
        resp = client.post("/api/v1/sessions",
            json={"requestedEnergyKwh": 30.0, "protocolIds": [1]},
            headers={"Authorization": f"Bearer {user_a_token}"})
        assert resp.status_code == 409

    def test_get_session_detail(self, user_a_token, user_b_token):
        # 创建 B 的会话
        resp = client.post("/api/v1/sessions",
            json={"requestedEnergyKwh": 50.0, "protocolIds": [1, 3]},
            headers={"Authorization": f"Bearer {user_b_token}"})
        session_id = resp.json()["data"]["sessionId"]

        # 查看详情
        resp = client.get(f"/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {user_b_token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "queued"

        # B 不能看 A 的会话
        resp = client.get(f"/api/v1/sessions/1",
            headers={"Authorization": f"Bearer {user_b_token}"})
        assert resp.status_code == 403


class TestSwitchStation:
    def test_switch_station_success(self, user_b_token):
        # 获取会话 ID
        resp = client.get("/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_b_token}"})
        session_id = resp.json()["data"]["activeSession"]["sessionId"]

        # 获取可换入选项
        resp = client.get(f"/api/v1/sessions/{session_id}/switch-options",
            headers={"Authorization": f"Bearer {user_b_token}"})
        assert resp.status_code == 200
        options = resp.json()["data"]["options"]
        if options:
            target_id = options[0]["id"]
            resp = client.post(f"/api/v1/sessions/{session_id}/switch-station",
                json={"targetStationId": target_id},
                headers={"Authorization": f"Bearer {user_b_token}"})
            assert resp.status_code == 200

    def test_cancel_queue_free(self, user_b_token):
        resp = client.get("/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_b_token}"})
        session_id = resp.json()["data"]["activeSession"]["sessionId"]

        resp = client.post(f"/api/v1/sessions/{session_id}/cancel",
            headers={"Authorization": f"Bearer {user_b_token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"
        assert resp.json()["data"]["bill"] is None  # 免费取消
```

### 前端人工检查

| 操作 | 预期结果 |
|------|----------|
| 登录后选择电量和协议，点击"开始充电" | 跳转到排队进度页，显示"已进入排队区，第 X 位" |
| 排队进度页定时刷新 | 排队位置更新 |
| 点击"换队"按钮，选择另一个桩 | 排队位置和桩名称更新 |
| 点击"取消排队" | 提示"免费取消"，确认后回到主页 |
| 刷新页面后恢复状态 | 仍显示排队中信息 |

---

## 阶段 4：自动调度循环

### 目标

实现后台调度循环，自动将排队区 → 等待区 → 充电区流转。
这是整个系统的核心动力，没有它所有车辆都卡在排队区。

### 前置条件

阶段 3 完成（需要排队区有车辆才能测试调度）。

### 给 Claude Code 的提示词

```
请实现完整的自动调度循环。参考 docs/design/04-编码前设计决策.md 中第 十三 章节的完整代码。

要求：
1. 完善 scheduler/dispatch_loop.py 中的 DispatchLoop 类
2. 实现 _tick_charging() — 推进充电进度
   - 扫描 status=charging 的会话
   - 按 elapsed_time × protocol.power_kw 计算 charged_energy
   - 如果 >= requested_energy_kwh，自动完成并生成账单
   
3. 实现 _dispatch_queue_to_waiting() — 排队区→等待区
   - 对每个 running 状态的桩
   - while 等待区有空位且排队区有车
   - 取排队区队首，移入等待区队尾
   - 更新 queue_position、zone、entered_waiting_at
   - 更新 station 的 queue_count 和 waiting_count

4. 实现 _dispatch_waiting_to_charging() — 等待区→充电区
   - 对每个 running 状态的桩
   - while 充电区有空位且等待区有车
   - 取等待区队首
   - 自动匹配兼容的最高功率协议
   - 移入充电区，开始充电
   - 更新 zone、protocol_id、started_charging_at

5. 完善 main.py 的 lifespan：
   - init_db() 后等待 2 秒
   - 启动 dispatch_loop.start()
   - 关闭时 dispatch_loop.stop()

6. 注意：
   - _best_match() 取用户支持 ∩ 充电桩支持的协议中功率最高的
   - 所有数据库操作完成后 commit()
   - 异常捕获防止循环退出
   - 调度日志写入 schedule_logs 表
```

### 预期可检查状况

| 检查项 | 方法 |
|--------|------|
| 启动后自动调度 | 排队中的车辆自动进入等待区 |
| 等待区满后排队区停止 | 等待区满（3 辆）后，排队区不再移入 |
| 充电区满后等待区停止 | 充电区满（2 台）后，等待区不再移入 |
| 充电进度推进 | 充电中车辆每 10s 已充电量增加 |
| 充满后自动完成 | 电量达到目标后 status=completed，生成账单 |
| 调度日志写入 | schedule_logs 表有对应记录 |

### 自动化测试脚本

```python
# backend/tests/test_stage4_dispatch.py
import pytest
import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_dispatch_flow():
    """测试完整的调度流转：排队→等待→充电→完成"""
    # 1. 注册并登录一个新用户
    plate = f"调度测试{int(time.time())}"
    resp = client.post("/api/v1/auth/register", json={
        "licensePlate": plate, "userName": "调度测试", "batteryCapacity": 100,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 4],
    })
    token = resp.json()["data"]["token"]

    # 2. 发起充电请求（充电量小一点，方便快速完成）
    resp = client.post("/api/v1/sessions",
        json={"requestedEnergyKwh": 0.5, "protocolIds": [1, 4]},
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    session_id = resp.json()["data"]["sessionId"]

    # 3. 等待调度循环执行几次（排队→等待→充电）
    time.sleep(15)  # 调度循环 10s 一次，等 15s 确保至少一次 tick

    # 4. 检查会话状态
    resp = client.get(f"/api/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"})
    data = resp.json()["data"]
    # 可能已经是 charging 或 completed（电量很小）
    assert data["status"] in ("charging", "completed", "waiting")

    # 5. 充电很小（0.5kWh），继续等待充满
    if data["status"] == "charging":
        time.sleep(15)
        resp = client.get(f"/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]

    # 6. 验证最终完成
    assert data["status"] == "completed" or data["chargedEnergyKwh"] > 0
```

### 前端人工检查

| 操作 | 预期结果 |
|------|----------|
| 刷新排队进度页 | 排队位置逐渐前移，最终进入等待区 |
| 切换到等待区后 | 显示"等待充电"状态，基础服务费变为 5.00 |
| 进入充电区后 | 显示充电进度条、当前协议、实时费用 |
| 电量到达目标后 | 自动跳转账单页 |

---

## 阶段 5：充电会话·充电阶段

### 目标

实现在充电过程中的用户操作：确认充电、修改电量、修改协议、停止充电。
至此，用户的完整充电流程全部走通。

### 前置条件

阶段 4（自动调度）完成。

### 给 Claude Code 的提示词

```
请实现充电阶段的用户操作接口。

需要实现：
1. POST /api/v1/sessions/:id/confirm-charging — 确认/拒绝开始充电
   - action=confirm：用户选择协议后确认开始
   - action=reject / 超时自动：取消并收基础服务费
   - confirm 时可选修改目标电量

2. PUT /api/v1/sessions/:id/energy — 修改目标电量
   - queued/waiting 态：任意 > 0
   - charging 态：必须 > chargedEnergyKwh
   - 返回 currentFee 快照 + estimatedEndTime + estimatedTotalFee

3. GET /api/v1/sessions/:id/protocol-options — 获取候选充电协议
   - 根据用户注册协议和当前桩支持协议计算交集

4. PUT /api/v1/sessions/:id/protocol — 修改支持的充电协议
   - 先调 protocol-options 获取候选列表
   - queued/waiting 态任意选，charging 态只能选当前桩支持的
   - charging 态不能移除当前使用的协议

5. POST /api/v1/sessions/:id/stop-charging — 结束充电
   - 仅 charging 态可用
   - 停止充电，生成完整账单

6. 充电完成自动通知流程：
   - 调度循环 _tick_charging 检测到充满
   - 自动生成 bill
   - 前端下次轮询 GET /sessions/:id 时看到 status=completed

参考 docs/design/01-API接口说明.md 中的对应接口定义。
所有接口在响应中携带 currentFee（当前实时费用）。
```

### 预期可检查状况

| 检查项 | 方法 |
|--------|------|
| 确认充电成功 | confirm-charging 返回 status=charging |
| 超时自动取消 | 不调用 confirm，60s 后自动 cancel |
| 修改电量成功 | PUT /energy 返回新目标电量 |
| 修改电量低于已充电量 | 返回 400 |
| 获取候选协议 | protocol-options 返回协议列表 |
| 修改协议成功 | PUT /protocol 返回更新后的列表 |
| 停止充电 | stop-charging 返回 complete + bill |
| 停止充电后轮询 | GET /sessions/:id 看到 status=completed |
| 账单已生成 | 数据库中 bills 表有对应记录 |

### 自动化测试脚本

```python
# backend/tests/test_stage5_session_charging.py
import pytest
import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def create_user_and_session():
    """helper：创建用户并进入充电状态"""
    plate = f"充电测试{int(time.time())}"
    resp = client.post("/api/v1/auth/register", json={
        "licensePlate": plate, "userName": "充电测试", "batteryCapacity": 100,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 4],
    })
    token = resp.json()["data"]["token"]

    client.post("/api/v1/sessions",
        json={"requestedEnergyKwh": 50.0, "protocolIds": [1, 4]},
        headers={"Authorization": f"Bearer {token}"})

    # 等待调度到充电区
    time.sleep(15)

    # 确认开始充电
    resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    session_id = resp.json()["data"]["activeSession"]["sessionId"]

    client.post(f"/api/v1/sessions/{session_id}/confirm-charging",
        json={"action": "confirm", "protocolId": 4},
        headers={"Authorization": f"Bearer {token}"})

    return token, session_id


class TestModifyEnergy:
    def test_modify_energy_success(self):
        token, session_id = create_user_and_session()
        resp = client.put(f"/api/v1/sessions/{session_id}/energy",
            json={"requestedEnergyKwh": 60.0},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["requestedEnergyKwh"] == 60.0


class TestModifyProtocol:
    def test_protocol_options(self):
        token, session_id = create_user_and_session()
        resp = client.get(f"/api/v1/sessions/{session_id}/protocol-options",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_modify_protocol(self):
        token, session_id = create_user_and_session()
        resp = client.put(f"/api/v1/sessions/{session_id}/protocol",
            json={"protocolIds": [1]},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


class TestStopCharging:
    def test_stop_charging(self):
        token, session_id = create_user_and_session()
        resp = client.post(f"/api/v1/sessions/{session_id}/stop-charging",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "completed"
        assert "bill" in data
        assert data["bill"]["totalFee"] > 0
```

### 前端人工检查

| 操作 | 预期结果 |
|------|----------|
| 进入充电区后弹出确认界面 | 显示"选择充电协议"和"确认开始"按钮 |
| 点击确认 | 开始充电，跳转充电进度页 |
| 不操作等待超时 | 自动取消，收基础服务费 |
| 充电进度页实时更新 | 进度条、已充电量、当前金额每 3~5 秒刷新 |
| 点击"修改电量" | 输入新值后提交，预估总费用更新 |
| 点击"修改协议" | 弹出可选协议列表，切换后更新 |
| 点击"停止充电" | 二次确认后停止，跳转账单页 |
| 达到目标电量自动停止 | 自动跳转账单页 |

---

## 阶段 6：账单与支付

### 目标

实现账单生成、详情查询、历史列表、模拟支付。

### 前置条件

阶段 5 完成（充电完成后生成账单）。

### 给 Claude Code 的提示词

```
请实现账单和支付相关的接口。

需要实现：

1. service/billing/ 模块：
   - service/billing/__init__.py
   - service/billing/engine.py — 计费引擎纯函数
     * calculate_electricity_fee(start, end, total_energy, prices) → FeeResult
     * calculate_service_fee(minutes, base_fee, tiers) → FeeResult
     * 电费按电价时段切片计算
     * 服务费按阶梯费率计算
   - service/billing/service.py — BillingService
     * generate_bill(session_id) → Bill
     * get_bill(bill_id) → Bill
     * get_user_bills(user_id, page, page_size, filters) → paginated list
     * process_payment(bill_id) → update payment_status

2. api/bills/ 模块：
   - GET /api/v1/bills — 当前用户的历史账单列表（分页）
   - GET /api/v1/bills/:id — 账单详情
   - POST /api/v1/bills/:id/pay — 模拟支付

3. 计费引擎详细逻辑：
   电费 = Σ(各时段 × 充电量 × 电价)
   服务费 = 基础服务费 + Σ(各阶梯分钟数 × 阶梯费率)
   充电量均匀分配到充电时长内的各电价时段

参考 docs/design/01-API接口说明.md 中第四部分 账单模块。
参考 docs/design/04-编码前设计决策.md 中第四章节 计费引擎核心算法。
```

### 预期可检查状况

| 检查项 | 方法 |
|--------|------|
| 账单详情完整 | GET /bills/:id 返回全部分时电费 + 服务费阶梯明细 |
| 电费计算正确 | 跨时段充电按比例分配 |
| 历史账单列表 | GET /bills 返回分页账单列表 |
| 支付成功 | POST /bills/:id/pay 返回 paid + transactionId |
| 重复支付失败 | 已支付账单再次 pay 返回 400 |
| 账单总金额一致 | electricityFee + serviceFee = totalFee |

### 自动化测试脚本

```python
# backend/tests/test_stage6_billing.py
import pytest
import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def create_completed_session():
    """helper：创建并完成一个充电会话"""
    plate = f"账单测试{int(time.time())}"
    resp = client.post("/api/v1/auth/register", json={
        "licensePlate": plate, "userName": "账单测试", "batteryCapacity": 100,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 4],
    })
    token = resp.json()["data"]["token"]

    # 发起充电（小电量快速完成）
    client.post("/api/v1/sessions",
        json={"requestedEnergyKwh": 0.3, "protocolIds": [1, 4]},
        headers={"Authorization": f"Bearer {token}"})

    time.sleep(25)  # 等调度 + 充电完成

    return token


class TestBilling:
    def test_bill_detail(self):
        token = create_completed_session()
        resp = client.get("/api/v1/bills", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        bills = resp.json()["data"]["list"]
        assert len(bills) > 0

        bill_id = bills[0]["billId"]
        resp = client.get(f"/api/v1/bills/{bill_id}",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["totalFee"] > 0
        assert data["electricityFee"] >= 0
        assert data["totalServiceFee"] > 0

    def test_payment(self):
        token = create_completed_session()
        resp = client.get("/api/v1/bills", headers={"Authorization": f"Bearer {token}"})
        bill_id = resp.json()["data"]["list"][0]["billId"]

        # 支付
        resp = client.post(f"/api/v1/bills/{bill_id}/pay",
            json={"paymentMethod": "wechat"},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["paymentStatus"] == "paid"
        assert "transactionId" in data

        # 重复支付
        resp = client.post(f"/api/v1/bills/{bill_id}/pay",
            json={"paymentMethod": "alipay"},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400
```

### 前端人工检查

| 操作 | 预期结果 |
|------|----------|
| 充电完成后自动跳转 | 显示账单页，包含分时电费、服务费阶梯明细 |
| 点击"查看详单" | 展开各时段电量电价、各阶梯时长费率 |
| 选择支付方式并确认 | 显示"支付成功"，展示交易流水号 |
| 进入"历史账单"页面 | 显示所有历史账单列表，可按状态筛选 |

---

## 阶段 7：管理端·队列管理与调度

### 目标

实现管理员查看所有队列、拖拽修改队列位置、在桩之间移动车辆、紧急停止并重新调度。

### 前置条件

阶段 3~5 完成（需要队列中有车辆才能管理）。

### 给 Claude Code 的提示词

```
请实现管理端的队列管理功能。

需要实现：
1. GET /api/v1/admin/queues — 查看所有队列
   - 返回所有充电桩的三个区域车辆列表
   - 包含每辆车的 sessionId, licensePlate, 位置, 目标电量

2. PUT /api/v1/admin/queues/reorder — 拖拽修改队列位置
   - 指定 stationId, zone(queue/waiting), sessionId, newPosition
   - 重新排列该区域中的所有车辆

3. PUT /api/v1/admin/queues/move — 拖拽移动到其他桩
   - 指定 sessionId, targetStationId, targetPosition
   - 将车辆从一个桩的队列移到另一个桩

4. 完善 POST /api/v1/admin/stations/:id/emergency-stop
   - 将当前桩排队区和等待区所有车辆重新调度到其他桩
   - 调度策略分别实现：shortest_time_single（逐个计算最优桩）
   - 记录调度日志

5. service/dispatch/strategy.py — 调度策略接口
   - 策略模式接口
   - ShortestTimeSingleStrategy 实现
```

### 预期可检查状况

| 检查项 | 方法 |
|--------|------|
| 查看所有队列 | GET /admin/queues 返回所有桩的队列 |
| 修改排队位置 | reorder 后排队顺序改变 |
| 移动到其他桩 | move 后车辆出现在目标桩的队列中 |
| 紧急停止 + 重分配 | emergency-stop 后排队/等待车辆转移到其他桩 |
| 调度日志写入 | schedule_logs 表有对应记录 |

### 前端人工检查

| 操作 | 预期结果 |
|------|----------|
| 进入管理后台"队列管理" | 显示所有充电桩的三区车辆列表 |
| 拖拽车辆到另一个位置 | 位置更新，其他车辆自动顺移 |
| 拖拽车辆到另一个桩 | 车辆出现在目标桩的队列中 |
| 点击"紧急停止" | 弹窗确认，选择算法后执行，车辆重分配 |
| 查看调度日志 | 日志列表显示执行记录 |

---

## 阶段 8：管理端·配置与报表

### 目标

实现管理员配置管理（全局配置、电价、服务费阶梯）和报表查看。

### 前置条件

阶段 6 完成（需要历史数据生成报表）。

### 给 Claude Code 的提示词

```
请实现管理端的配置和报表功能。

需要实现：

1. api/admin/config/ 模块：
   - GET /api/v1/admin/config — 获取全部配置（调度算法、服务费、电价、阶梯）
   - PUT /api/v1/admin/config — 统一更新配置（全部可选，只传需要修改的字段）

2. api/admin/sessions/ 模块：
   - GET /api/v1/admin/sessions — 查看所有用户会话（分页，支持按状态/桩/用户筛选）
   - GET /api/v1/admin/sessions/:id — 查看任意会话详情

3. api/admin/bills/ 模块：
   - GET /api/v1/admin/bills — 查看所有账单（分页，支持按用户/桩/支付状态筛选）
   - GET /api/v1/admin/bills/:id — 查看任意账单详情

4. api/admin/reports/ 模块：
   - GET /api/v1/admin/reports/charging-volume — 充电量统计
   - GET /api/v1/admin/reports/revenue — 收入统计
   - GET /api/v1/admin/reports/utilization — 充电桩利用率
```

### 预期可检查状况

| 检查项 | 方法 |
|--------|------|
| 获取全局配置 | GET /admin/config 返回所有配置 |
| 更新配置 | 修改后再次 GET 验证值已变化 |
| 查看所有会话 | GET /admin/sessions 分页返回 |
| 按状态筛选会话 | 参数 status=charging 只返回充电中 |
| 查看任意账单 | GET /admin/bills/:id 返回完整账单 |
| 充电量报表 | 返回有数据的统计图表 |
| 收入报表 | 总收入和明细数据 |

### 前端人工检查

| 操作 | 预期结果 |
|------|----------|
| 进入"系统配置"页 | 显示当前调度算法、服务费、电价、阶梯 |
| 修改电价并保存 | 再次打开配置页显示新电价 |
| 进入"会话管理" | 显示所有用户的会话列表，可筛选 |
| 进入"账单管理" | 显示所有用户的账单列表 |
| 进入"报表"页 | 充电量统计、收入统计、利用率图表 |

---

## 阶段 9：前端接入与联调

### 目标

将前后的 Vue 前端接入后端 API，完成完整的用户界面。

### 前置条件

阶段 0~8 全部完成，后端 API 稳定。

### 提示词

```
请基于 docs/design/01-API接口说明.md 中的 API 定义，
搭建 Vue 3 + Element Plus 前端项目。

要求：
1. 前端根目录 .env 文件可配置 VITE_API_BASE_URL（后端地址）
2. 所有 API 调用封装到 src/api/ 目录下，按模块分文件
3. 页面路由：
   - /login, /register
   - /home（充电桩列表 + 发起充电）
   - /session/:id（排队/充电进度页）
   - /bill/:id（账单详情）
   - /admin/*（管理后台）

4. 核心交互页面：
   - 充电桩列表页：显示所有桩的状态
   - 充电进度页：轮询 + 进度条 + 实时金额
   - 账单页：分时明细 + 支付按钮
   - 管理后台：配置、队列管理、报表
```

---

## 阶段 10：补丁与优化

### 目标

修复集成测试发现的问题，性能优化，代码清理。

### 可能的问题列表

| 问题 | 现象 | 修复方向 |
|------|------|----------|
| 调度循环竞争条件 | 两个 tick 同时操作同一会话 | 加 asyncio.Lock |
| SQLite 并发写入慢 | 调度循环和 API 同时写 DB | 考虑 SQLModel session 管理 |
| 前端 Token 过期 | 401 不跳登录 | 前端 axios 拦截器统一处理 |
| 计费精度 | float 累加误差 | 使用 Decimal 或 round |
| 种子数据重复 | 重启服务后重复插入 | init_db 加幂等检查 |

---

> 文档版本：v1.0 | 2026-06-09
