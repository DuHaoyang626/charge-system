# 智能充电桩调度计费系统

基于 FastAPI + SQLModel + Vue 3 + Element Plus 的充电桩调度计费后端 API 与前端管理界面。

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Python 3.14+ / FastAPI | REST API，自动生成 Swagger 文档 |
| 数据库 | SQLite（开发）/ SQLModel ORM | 零配置，文件级数据库 |
| 鉴权 | JWT (python-jose) + bcrypt | Token 有效期 24 小时 |
| 前端框架 | Vue 3 + Vite + TypeScript | 组合式 API + `<script setup>` |
| UI 组件 | Element Plus | 中文语言包，全局定制 |
| 状态管理 | Pinia | 认证/充电桩/会话状态 |
| HTTP 请求 | Axios | JWT 拦截器 + 401 跳转 |

## 快速启动

### 环境要求

- Python ≥ 3.11
- Node.js ≥ 18

### 1. 启动后端

```powershell
# 进入后端目录
cd backend

# 安装依赖（首次）
pip install -e ".[dev]"

# 启动开发服务器（热重载）
python -m uvicorn main:app --reload
```

后端运行在 `http://127.0.0.1:8000`

| 地址 | 说明 |
|------|------|
| `http://127.0.0.1:8000/docs` | Swagger API 文档 |
| `http://127.0.0.1:8000/redoc` | ReDoc 文档 |
| `http://127.0.0.1:8000/health` | 健康检查 |

> 首次启动时自动创建 SQLite 数据库 `backend/data/charge_system.db` 并写入种子数据：
> - 5 条充电协议（AC 7kW ~ DC 250kW）
> - 2 台演示充电桩（A区-01号桩 / B区-02号桩）
> - 1 个管理员账号（ADMIN / admin123）
> - 电价时段 / 服务费阶梯 / 全局配置

### 2. 启动前端

```powershell
# 进入前端目录
cd frontend

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

前端运行在 `http://localhost:5173`

Vite 开发服务器会自动代理 `/api` 请求到后端 `http://127.0.0.1:8000`（无需单独配置 CORS）。

### 3. 同时启动（两个终端）

```powershell
# 终端 1 — 后端
cd backend
python -m uvicorn main:app --reload

# 终端 2 — 前端
cd frontend
npm run dev
```

打开浏览器访问 `http://localhost:5173`

## 页面引导

| 页面 | 路径 | 说明 |
|------|------|------|
| 登录 | `/login` | 使用车牌号 + 密码登录 |
| 注册 | `/register` | 创建新账号（车牌号 + 协议选择） |
| 主页 | `/` | 用户信息 + 活动会话展示 |
| Swagger | `http://127.0.0.1:8000/docs` | 后端所有 API 接口文档 |

### 人工检查流程

| 操作 | 预期结果 |
|------|----------|
| 注册页填写信息并提交 | 返回成功，自动跳转到主页 |
| 使用已注册的车牌号再次注册 | 提示"该车牌号已注册" |
| 登录页输入正确账号密码 | 成功登录，跳转主页 |
| 登录页输入错误密码 | 提示"账号或密码错误" |
| 手动清除 token 后刷新页面 | 跳转回登录页 |

### 默认管理员账号

| 字段 | 值 |
|------|----|
| 车牌号 | `ADMIN` |
| 密码 | `admin123` |

## 运行测试

```powershell
cd backend

# 运行所有测试（默认使用临时 SQLite 文件）
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_stage1_auth.py -v

# 运行测试桩示例（展示三种测试模式）
python -m pytest tests/test_example_mock.py -v
```

当前测试分为两类：

### 集成测试（原有测试）
- 阶段 0（基础设施）：4 项 — 模块导入、种子数据、JWT 签发、密码哈希
- 阶段 1（认证模块）：3 类 — 注册/登录/用户信息全流程
- 阶段 2（充电桩模块）：用户端查询 + 管理端增删改
- 阶段 3-6（会话/调度/计费）：完整业务流程

### 测试桩示例（`test_example_mock.py`）
展示三种测试模式：
1. **`in_memory_db` fixture** — 内存 SQLite，快且保真
2. **`mock_client` / `seeded_client`** — HTTP 接口层单元测试
3. **`unittest.mock` 直接 Mock** — 纯单元测试，零数据库依赖

### 测试模式切换

项目支持三种测试模式，通过 fixture 名选择：

| 模式 | Fixture | 数据库 | 速度 | 适用场景 |
|------|---------|--------|------|----------|
| 集成测试 | `client` / `db_session` | 临时 SQLite 文件 | 中 | 完整业务流程验证 |
| 内存 DB | `in_memory_db` / `mock_client` | 内存 SQLite | 快 | Service 层单测 |
| 纯 Mock | `@patch` / `MagicMock` | 无 | 最快 | 纯逻辑 / 异常路径测试 |

在测试函数中通过参数引用不同的 fixture 即可切换：

```python
# 方式 A：内存数据库 Service 测试
def test_service(in_memory_db):
    from service.account.service import register
    result = register(...)
    assert result["token"]

# 方式 B：HTTP 接口测试（内存数据库）
def test_api(mock_client):
    resp = mock_client.get("/health")
    assert resp.status_code == 200

# 方式 C：HTTP 接口测试（含种子数据）
def test_api_with_seed(seeded_client, admin_token):
    resp = seeded_client.get("/api/v1/stations",
        headers={"Authorization": f"Bearer {admin_token}"})
    assert len(resp.json()["data"]["stations"]) >= 5

# 方式 D：纯 Mock 单元测试
@patch("service.account.service.Session")
def test_login_mock(mock_session):
    mock_db = MagicMock()
    mock_db.exec().first.return_value = mock_user
    mock_session.return_value.__enter__.return_value = mock_db
    result = login(...)
    assert result["token"]
```

## 项目结构

```
charge-system/
├── backend/
│   ├── api/                    # 路由层
│   │   ├── auth/               # 认证（注册/登录）
│   │   ├── users/              # 用户信息
│   │   ├── stations/           # 充电桩
│   │   ├── sessions/           # 充电会话
│   │   ├── bills/              # 账单
│   │   ├── protocols/          # 充电协议
│   │   └── admin/              # 管理端（config/stations/sessions/bills/queues/reports）
│   ├── core/                   # 核心基础设施
│   │   ├── config.py           # 配置加载
│   │   ├── database.py         # 数据库初始化 + 种子数据 + set_engine() 切换
│   │   ├── security.py         # JWT + 密码哈希
│   │   ├── exceptions.py       # 业务异常 + 错误码
│   │   ├── exception_handlers.py
│   │   ├── deps.py             # FastAPI 依赖注入
│   │   ├── response.py         # 统一响应格式
│   │   └── test_utils.py       # 测试桩 + 工厂函数 + Mock 工具
│   ├── model/                  # SQLModel 数据模型
│   ├── service/                # 业务逻辑层
│   ├── scheduler/              # 定时调度
│   ├── tests/                  # 测试
│   ├── data/                   # SQLite 数据库文件
│   ├── main.py                 # 应用入口
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── api/                # API 调用层（Axios + 拦截器）
│   │   ├── router/             # Vue Router + 导航守卫
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── views/              # 页面组件
│   │   │   ├── auth/           # 登录/注册
│   │   │   ├── home/           # 主页
│   │   │   ├── station/        # 充电桩
│   │   │   ├── session/        # 充电会话
│   │   │   └── bill/           # 账单
│   │   ├── components/         # 通用组件
│   │   └── utils/              # 工具函数
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                       # 设计文档
├── DESIGN.md                   # 前端设计规范
└── README.md
```

## 环境变量

后端 `.env` 文件（`backend/.env`）：

```bash
# JWT 密钥（生产环境务必修改）
JWT_SECRET_KEY=change-this-to-a-random-string-at-least-32-chars
# 数据库连接（SQLite 文件路径）
DATABASE_URL=sqlite:///./data/charge_system.db
```

### 测试环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 测试数据库连接（conftest.py 自动设为临时文件） | `sqlite:///./data/charge_system.db` |
| `CHARGE_TEST_MODE` | 测试模式（可选 `mock`） | 未设置时使用临时 SQLite 文件 |

前端环境变量（`frontend/env/.env.development`）：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```
