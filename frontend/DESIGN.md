# Design System: 智能充电桩调度计费系统

> 统一前端设计规范，覆盖 Vue 3 + Element Plus 实现的技术架构、组件体系、视觉美学与数据流。
> **目标**：在多次迭代中保持功能一致性与界面统一性。

---

## 1. Visual Theme & Atmosphere

### 1.1 视觉调性

**工业精密 · 数据清晰 · 状态直观**

- **密度**：日常 App 平衡级（5/10）— 主页和信息页保持呼吸感；仪表盘和队列页可适度紧凑（6/10）
- **变化度**：规整偏不对称（5/10）— 卡片规整排列，但通过状态色块、进度条长度产生视觉节奏
- **动效**：克制流畅（4/10）— 仅在状态切换、轮询更新时有微过渡，无冗余装饰动效

### 1.2 氛围关键词

`Utility-Grade` `Clean` `Status-Driven` `Data-Transparent` `Trustworthy` `No-Nonsense`

系统传达的是**工业级的可靠感**——每个充电状态一目了然，费用计算透明可见，用户信任系统给出的预估时间。

---

## 2. Color Palette & Roles

### 2.1 基础色板

| 色名 | 色值 | 角色 |
|------|------|------|
| **画布底色** | `#F5F5F5` (Neutral-100) | 页面主背景 |
| **纯白表面** | `#FFFFFF` | 卡片、容器、侧边栏填充 |
| **墨黑文字** | `#1A1A1A` (Zinc-950) | 主文字、标题 |
| **钢灰辅助** | `#737373` (Neutral-500) | 次要文字、描述、元数据 |
| **淡灰边框** | `rgba(209, 213, 219, 0.6)` | 卡片 1px 边框、分割线 |
| **微弱阴影** | `0 1px 3px rgba(0,0,0,0.06)` | 卡片默认阴影 |

### 2.2 状态语义色（充电系统核心色）

| 色名 | 色值 | 用途 | 场景 |
|------|------|------|------|
| **待充蓝** | `#2563EB` (Blue-600) | 排队中、等待中标识 | `queued` / `waiting` 状态标签、进度条底色 |
| **充电绿** | `#16A34A` (Green-600) | 充电中标识 | `charging` 状态标签、活跃进度条、功率指示 |
| **完成灰** | `#6B7280` (Gray-500) | 已完成、已取消 | `completed` / `cancelled` 灰显 |
| **错误红** | `#DC2626` (Red-600) | 异常、错误 | `error` 状态、网络异常提示、校验错误 |
| **警告黄** | `#D97706` (Amber-600) | 停止中、待支付 | `stopping`、`unpaid` 标签 |
| **费用橙** | `#EA580C` (Orange-600) | 金额高亮 | 总费用数字、电费显示 |

### 2.3 品牌色

| 色名 | 色值 | 角色 |
|------|------|------|
| **品牌主色** | `#2563EB` (Blue-600) | Element Plus 全局主色，CTA 按钮，导航激活态 |
| **品牌浅色** | `#DBEAFE` (Blue-100) | 选中态背景，信息提示条底色 |
| **品牌深色** | `#1E40AF` (Blue-800) | 深色文字链接、Hover 加深 |

### 2.4 禁止规则

- ❌ 禁止纯黑色 `#000000` — 使用 `#1A1A1A`
- ❌ 禁止霓虹/外发光阴影
- ❌ 禁止紫色/粉色渐变按钮
- ❌ 禁止饱和度过高的色彩（状态色控制在 saturation < 70%）
- ❌ 禁止 Emoji 替代图标 — 全部使用 Element Plus 内置图标 `el-icon-*`

---

## 3. Typography Rules

### 3.1 字体栈

```css
--font-family: 'Inter Variable', -apple-system, BlinkMacSystemFont, 'Segoe UI',
               'PingFang SC', 'Microsoft YaHei', sans-serif;
--font-mono: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', monospace;
```

| 层级 | 字重 | 字号 | 行高 | 字间距 | 场景 |
|------|------|------|------|--------|------|
| **页面标题** | Semibold 600 | 24px / 1.5rem | 1.3 | -0.01em | 页面级 H1 |
| **卡片标题** | Medium 500 | 18px / 1.125rem | 1.4 | 0 | 卡片式区块标题 |
| **正文** | Regular 400 | 14px / 0.875rem | 1.6 | 0 | 表单 Label、描述、列表 |
| **辅助文字** | Regular 400 | 12px / 0.75rem | 1.5 | 0 | 时间戳、元数据、脚注 |
| **金额数字** | Semibold 600 | 20px / 1.25rem | 1.3 | -0.02em | 费用展示（等宽字体） |
| **状态标签** | Medium 500 | 12px / 0.75rem | 1.4 | 0.02em | Badge / Tag 文字 |

### 3.2 禁止规则

- ❌ 禁止 `Georgia` / `Times New Roman` / `Garamond` 等衬线字体
- ❌ 禁止全大写标题（ACRONYM 或短标识除外）
- ❌ 页面标题不使用超大字号（不超过 28px）
- ❌ 金额数字必须使用等宽字体，保证小数点对齐

---

## 4. Technical Architecture

### 4.1 项目结构

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── env.d.ts
├── tsconfig.json
│
├── public/
│   └── favicon.svg
│
├── src/
│   ├── main.ts                          # 入口：注册 Element Plus + Router + Pinia
│   ├── App.vue                          # 根组件：RouterView + 全局布局壳
│   │
│   ├── api/                             # API 调用层
│   │   ├── request.ts                   # Axios 实例 + 拦截器（JWT 注入/401 处理）
│   │   ├── auth.ts                      # POST /auth/register, POST /auth/login
│   │   ├── station.ts                   # GET /stations, GET /stations/:id
│   │   ├── session.ts                   # 充电会话所有接口
│   │   ├── bill.ts                      # 账单接口
│   │   └── admin/                       # 管理端接口
│   │       ├── config.ts
│   │       ├── station.ts
│   │       ├── session.ts
│   │       ├── bill.ts
│   │       ├── queue.ts
│   │       └── report.ts
│   │
│   ├── router/
│   │   └── index.ts                     # Vue Router 配置 + 路由守卫
│   │
│   ├── stores/                          # Pinia 状态管理
│   │   ├── auth.ts                      # token + user 信息 + 登录/登出
│   │   ├── station.ts                   # 充电桩列表缓存
│   │   └── session.ts                   # 当前活动会话轮询状态
│   │
│   ├── views/
│   │   ├── auth/
│   │   │   ├── LoginView.vue            # 登录页
│   │   │   └── RegisterView.vue         # 注册页
│   │   ├── home/
│   │   │   └── HomeView.vue             # 主页（桩概览 + 快捷入口）
│   │   ├── station/
│   │   │   ├── StationListView.vue      # 充电桩列表
│   │   │   └── StationDetailView.vue    # 充电桩详情（三区队列）
│   │   ├── session/
│   │   │   ├── SessionCreateView.vue    # 发起充电（选电量+协议）
│   │   │   ├── SessionProgressView.vue  # 充电/排队进度页（轮询核心）
│   │   │   └── SessionConfirmView.vue   # 充电确认（协议选择+倒计时）
│   │   ├── bill/
│   │   │   ├── BillListView.vue         # 历史账单列表
│   │   │   └── BillDetailView.vue       # 账单详情（分时明细）
│   │   └── admin/
│   │       ├── DashboardView.vue         # 管理仪表盘
│   │       ├── ConfigView.vue            # 全局配置
│   │       ├── StationManageView.vue     # 充电桩管理
│   │       ├── SessionManageView.vue     # 会话管理
│   │       ├── BillManageView.vue        # 账单管理
│   │       ├── QueueManageView.vue       # 队列管理（拖拽）
│   │       └── ReportView.vue            # 报表统计
│   │
│   ├── components/                      # 通用组件
│   │   ├── AppLayout.vue                # 全局布局（侧边栏+顶栏+内容区）
│   │   ├── AdminLayout.vue              # 管理端布局
│   │   ├── ChargingStatusBadge.vue      # 充电状态标签（六色）
│   │   ├── StationStatusBadge.vue       # 充电桩状态标签
│   │   ├── ProgressWithLabel.vue        # 进度条+百分比
│   │   ├── FeeDisplay.vue               # 费用展示（金额高亮）
│   │   ├── QueuePositionCard.vue        # 排队位置卡片
│   │   ├── SessionTimeline.vue          # 会话时间轴（三区流转）
│   │   └── EmptyState.vue               # 空状态占位
│   │
│   └── utils/
│       ├── format.ts                    # 时间/金额/百分比格式化
│       ├── constants.ts                 # 状态枚举、映射文案
│       └── polling.ts                   # 轮询工具（带退避策略）
│
└── env/
    ├── .env.development                 # VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
    └── .env.production                  # 生产环境配置
```

### 4.2 路由设计

```typescript
// 路由表
const routes = [
  // 认证（无 Layout 壳）
  { path: '/login',    component: LoginView },
  { path: '/register', component: RegisterView },

  // 用户端（AppLayout 壳）
  { path: '/',             component: AppLayout,
    children: [
      { path: '',          component: HomeView },              // 主页
      { path: 'stations',  component: StationListView },        // 充电桩列表
      { path: 'stations/:id', component: StationDetailView },   // 桩详情
      { path: 'sessions/create', component: SessionCreateView }, // 发起充电
      { path: 'sessions/:id', component: SessionProgressView },  // 会话进度
      { path: 'sessions/:id/confirm', component: SessionConfirmView }, // 充电确认
      { path: 'bills',     component: BillListView },           // 我的账单
      { path: 'bills/:id', component: BillDetailView },         // 账单详情
    ]
  },

  // 管理端（AdminLayout 壳，需 admin 权限）
  { path: '/admin',        component: AdminLayout,
    children: [
      { path: '',          component: DashboardView },
      { path: 'config',    component: ConfigView },
      { path: 'stations',  component: StationManageView },
      { path: 'sessions',  component: SessionManageView },
      { path: 'bills',     component: BillManageView },
      { path: 'queues',    component: QueueManageView },
      { path: 'reports',   component: ReportView },
    ]
  },
]
```

### 4.3 路由守卫

```typescript
// router/index.ts — 导航守卫逻辑
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  // 认证页：已登录则跳转主页
  if (to.path === '/login' || to.path === '/register') {
    return auth.isLoggedIn ? next('/') : next()
  }

  // 管理端：需 admin 角色
  if (to.path.startsWith('/admin')) {
    if (!auth.isLoggedIn) return next('/login')
    if (auth.user?.role !== 'admin') return next('/')
    return next()
  }

  // 用户端：需登录
  if (!auth.isLoggedIn) return next('/login')

  next()
})
```

### 4.4 API 层（Axios 拦截器）

```typescript
// api/request.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15000,
})

// 请求拦截器：自动注入 JWT
api.interceptors.request.use(config => {
  const token = useAuthStore().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理 + 401 跳登录
api.interceptors.response.use(
  res => res.data,
  error => {
    if (error.response?.status === 401) {
      useAuthStore().logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)
```

### 4.5 Pinia Store 结构

```typescript
// stores/auth.ts — 认证状态
interface AuthState {
  token: string | null
  user: UserInfo | null
}
// actions: login(), register(), logout(), fetchUserInfo()
// getters: isLoggedIn, isAdmin, activeSession

// stores/station.ts — 充电桩状态
interface StationState {
  stations: Station[]
  loading: boolean
}
// actions: fetchStations(), fetchStationDetail(id)

// stores/session.ts — 活动会话（轮询核心）
interface SessionState {
  activeSession: SessionDetail | null
  pollingInterval: number | null
  pollingCount: number
}
// actions: startPolling(sessionId), stopPolling(), createSession()
```

---

## 5. Component Stylings

### 5.1 Element Plus 全局定制

```scss
// 覆盖 Element Plus 变量
$--color-primary: #2563EB;
$--color-success: #16A34A;
$--color-warning: #D97706;
$--color-danger: #DC2626;
$--color-info: #6B7280;
$--border-radius-base: 8px;
$--font-size-base: 14px;
```

| 组件 | 定制说明 |
|------|----------|
| **Button** | 扁平无外发光。Primary 使用品牌蓝。Active 态 `translateY(-1px)` 微按压感。危险操作使用 Red-600 |
| **Card** | `border-radius: 12px`，`padding: 20px`，默认阴影 `0 1px 3px rgba(0,0,0,0.06)`，hover 升至 `0 4px 12px rgba(0,0,0,0.1)` |
| **Tag/Badge** | 根据 2.2 状态语义色映射。圆角 `16px`，字号 `12px`，内边距 `4px 10px` |
| **Table** | 无竖线，行高 `48px`，hover 行浅蓝底 `#F0F6FF` |
| **Form Input** | Label 在输入框上方（非浮动标签），聚焦时边框变品牌蓝，错误提示红色在输入框下方 |
| **Dialog** | `border-radius: 16px`，顶部无标题栏，内容区直接展示操作确认 |
| **Progress** | 圆形进度条用于充电百分比；线性进度条用于排队位置占比 |
| **Tabs** | 下划线式，激活态品牌蓝 2px 底边 |

### 5.2 自定义通用组件

#### ChargingStatusBadge

| 状态 | 色值 | 标签文案 |
|------|------|----------|
| `queued` | Blue-600 `#2563EB` | 排队中 |
| `waiting` | Blue-500 `#3B82F6` | 等待中 |
| `charging` | Green-600 `#16A34A` | 充电中 |
| `completed` | Gray-500 `#6B7280` | 已完成 |
| `cancelled` | Gray-400 `#9CA3AF` | 已取消 |
| `paid` | Green-700 `#15803D` | 已支付 |
| `unpaid` | Amber-600 `#D97706` | 未支付 |

#### StationStatusBadge

| 状态 | 色值 | 标签 | 指示点 |
|------|------|------|--------|
| `running` | Green-600 | 运行中 | 绿色实心圆点 |
| `stopping` | Amber-600 | 停止中 | 黄色空心圆环 |
| `stopped` | Gray-500 | 已停止 | 灰色实心圆点 |
| `error` | Red-600 | 异常 | 红色感叹号图标 |

#### FeeDisplay

- 总费用数字使用 `font-mono` + `font-semibold` + Orange-600
- 明细项以 `el-table` 呈现，左列时段名称，右列金额
- 电费与服务费之间以 1px 虚线分割

#### QueuePositionCard

- 大号数字显示当前位置（如 `#3`）
- 下方显示"当前排队：X 人"
- 当位置 <= 1 时，显示"即将轮到您"动画（脉冲绿点）
- 支持换队按钮（仅在 queued 状态显示）

#### EmptyState

- 居中构图：Element Plus 图标 + 说明文案 + 建议操作按钮
- 无数据场景：`el-icon-empty` + "暂无充电记录" + "去充电"按钮
- 无搜索结果：`el-icon-search` + "没有找到匹配结果" + "清除筛选"链接

#### LoadingState

- 列表加载：使用 Element Plus `el-skeleton` 组件，行列匹配实际卡片尺寸
- 页面加载：顶部细长线性进度条（NProgress 风格）
- 提交等待：按钮内显示 `loading` 态，禁止重复点击
- 禁止使用全屏居中旋转圆环

### 5.3 页面通用模式

| 模式 | 规则 |
|------|------|
| **列表页** | 顶部搜索/筛选栏 + 列表/卡片内容 + 底部分页（`el-pagination`） |
| **详情页** | 顶部返回按钮 + 标题 + 概览卡片组 + 明细表格 |
| **表单页** | 单列布局，字段不超过 8 个不分组，超过则用 `el-collapse` 折叠次要项 |
| **确认弹窗** | `el-message-box`，明确说明操作后果（如"将收取基础服务费 ¥5.00"） |
| **成功反馈** | `ElMessage.success()` 顶部弹出，绿色，2 秒后自动消失 |
| **错误反馈** | `ElMessage.error()` 顶部弹出，红色，需手动关闭（网络错误除外） |

---

## 6. Page Specifications

### 6.1 认证页（LoginView / RegisterView）

| 元素 | 规格 |
|------|------|
| **布局** | 居中卡片式，宽度 `420px` max，垂直居中 |
| **Logo/标题** | 顶部展示 app 名称 + 系统图标，无背景图 |
| **表单** | 注册 6 字段（车牌/用户名/电池容量/密码/确认密码/协议选择），登录 2 字段 |
| **协议选择** | `el-select` 多选模式，options 从 `GET /protocols` 加载 |
| **提交按钮** | 全宽 primary 按钮，loading 态避免重复提交 |
| **跳转链接** | 底部文字："已有账号？去登录" / "没有账号？去注册" |
| **错误展示** | `el-form` 内联校验 + 顶部 `ElAlert` 显示业务错误 |

### 6.2 主页（HomeView）

| 区域 | 内容 |
|------|------|
| **顶部** | 用户信息（车牌号 + 昵称）+ 当前费用/余额 + 设置入口 |
| **活动会话卡片** | 如有 activeSession，大卡片展示：状态标签 + 桩名 + 进度条 + "查看详情"按钮 |
| **充电桩概览** | 横向滚动卡片列表，每卡片显示：桩名 + 状态 + 三区占位条 + "发起充电"按钮 |
| **快捷入口** | 底部：我的账单、排队情况（如有 activeSession 替换为当前会话） |

### 6.3 充电桩详情（StationDetailView）

| 区域 | 内容 |
|------|------|
| **顶部** | 桩名 + 状态标签 + 返回按钮 |
| **三区 Tabs** | `el-tabs` 切换：排队区 / 等待区 / 充电区 |
| **排队区列表** | 显示 position + 车牌号（脱敏）+ 目标电量 + 预估等待时间 |
| **等待区列表** | 显示 position + 车牌号 + 已等待时间 |
| **充电区列表** | 显示 position + 车牌号 + 当前协议 + 进度条 + 预估结束时间 |
| **协议列表** | 底部折叠面板展示该桩支持的所有协议 |

### 6.4 会话进度页（SessionProgressView）— 轮询核心

这是最关键的页面，实现 3~5 秒轮询逻辑：

| 状态 | 界面表现 |
|------|----------|
| **queued** | 大号排队位置数字 + 目标桩名 + 预估等待倒计时 + "换队"按钮 + "取消"按钮 |
| **waiting** | 等待图标 + "即将进入充电区"文字 + 已收取基础服务费提示 + "取消(收费)"按钮 |
| **charging** | 圆形进度环 + 已充电量/目标电量 + 当前协议 + 已充电时长 + 实时费用卡片（每轮询更新）+ 停止充电按钮 |
| **completed** | 完成动画（对勾图标）+ 最终电量 + 费用总计 + "查看账单"按钮 |
| **cancelled** | 灰色提示 + 如有费用则展示账单入口 |

**轮询逻辑实现**：

```typescript
// stores/session.ts
async startPolling(sessionId: number) {
  this.stopPolling()
  this.pollingInterval = setInterval(async () => {
    try {
      const res = await getSessionDetail(sessionId)
      this.activeSession = res.data

      if (['completed', 'cancelled'].includes(res.data.status)) {
        this.stopPolling()
        if (res.data.bill?.billId) {
          router.push(`/bills/${res.data.bill.billId}`)
        }
      }
    } catch (err) {
      if (err.response?.status === 403 || err.response?.status === 404) {
        this.stopPolling()
        router.push('/')
      }
    }
  }, 3000)
}
```

### 6.5 充电确认页（SessionConfirmView）

| 元素 | 规格 |
|------|------|
| **触发时机** | 轮询检测到 `status: "waiting"` 且 `zone: "charging"` 时自动跳转 |
| **倒计时** | 顶部显式 60 秒倒计时条，红色警告超时将收取服务费 |
| **协议选择** | 单选框列表，默认高亮最高功率兼容协议 |
| **电量调整** | 数字输入框，默认原目标电量，下限 = `chargedEnergyKwh` |
| **操作按钮** | "确认开始充电"(primary) + "不使用，退出"(default) |
| **自动提交** | 倒计时归零自动提交 `action: "reject"` |

### 6.6 账单页（BillListView / BillDetailView）

| 场景 | 界面 |
|------|------|
| **列表** | 时间倒序，每项：日期 + 桩名 + 电量 + 总费用 + 支付状态标签 |
| **筛选** | `el-select` 按支付状态筛选 + `el-date-picker` 按日期范围 |
| **详情** | 顶部用户/桩摘要 → 电费分时明细表 → 服务费阶梯明细表 → 合计行（橙底加粗） |
| **支付** | 底部固定栏：总金额 + "去支付"按钮（unpaid 状态）；灰色"已支付"(paid 状态） |
| **支付成功** | `ElMessage.success()` + 2 秒后返回账单列表 |

### 6.7 管理端页面

| 页面 | 内容 |
|------|------|
| **Dashboard** | 4 指标卡片（在线桩数/活跃会话/今日充电量/今日收入）+ 桩利用率柱状图 |
| **Config** | `el-form` 展示所有全局配置，一个"保存"按钮提交 `PUT /admin/config` |
| **StationManage** | 桩列表 + 创建/编辑/删除/启停操作 |
| **SessionManage** | 所有用户会话列表 + 按状态/桩/人筛选 |
| **BillManage** | 所有用户账单列表 + 多维度筛选 |
| **QueueManage** | 各桩队列可视化展示 + 拖拽调整位置 |
| **Reports** | 充电量/收入/利用率三个 Tab，支持日期范围和粒度切换 |

---

## 7. Layout Principles

### 7.1 用户端布局（AppLayout）

```
┌─────────────────────────────────────┐
│  TopBar                              │
│  汉堡菜单 | 系统名称 | 用户信息 | 登出│
├─────────────────────────────────────┤
│                                     │
│          RouterView                  │
│         (页面内容区)                  │
│                                     │
├─────────────────────────────────────┤
│  BottomNav (移动端) / 无             │
│  主页 | 充电桩 | 账单 | 我的          │
└─────────────────────────────────────┘
```

- **桌面**：左侧可收起窄侧边栏（`240px`），顶部状态栏固定
- **移动**：顶部状态栏简化，底部 Tab 导航

### 7.2 管理端布局（AdminLayout）

```
┌──────────────┬──────────────────────────────┐
│   Sidebar    │                              │
│   仪表盘     │       RouterView              │
│   配置       │      (内容区)                 │
│   充电桩     │                              │
│   会话       │                              │
│   账单       │                              │
│   队列       │                              │
│   报表       │                              │
├──────────────┴──────────────────────────────┤
│               Footer (版本号)                │
└─────────────────────────────────────────────┘
```

- **桌面**：侧边栏 `220px` 固定，深色背景 `#1E293B`，菜单项白色文字
- **移动**：侧边栏收起为汉堡菜单

### 7.3 响应式断点

| 断点 | 宽度 | 行为 |
|------|------|------|
| **手机** | `< 768px` | 单列布局，底部 Tab 导航，充电桩卡片全宽 |
| **平板** | `768px ~ 1024px` | 双列卡片网格，保留侧边栏图标模式 |
| **桌面** | `> 1024px` | 三区队列并排，侧边栏全展开 |

### 7.4 布局规则

- 内容区最大宽度 `1400px`，居中
- 所有页面 `min-height: 100dvh`，防止 iOS Safari 底部跳跃
- 禁止横向溢出滚动
- `clamp()` 函数控制响应式间距：`padding: clamp(16px, 4vw, 32px)`
- 所有交互元素最小触控面积 `44px`

---

## 8. Data Flow & State Management

### 8.1 JWT 令牌生命周期

```
┌──────────────┐     ┌───────────────┐     ┌───────────────┐
│  登录/注册    │────>│  存入 Pinia   │────>│  Axios 拦截器   │
│  获取 token   │     │  auth.token   │     │  自动注入 Header│
└──────────────┘     └───────────────┘     └───────────────┘
                                                    │
                          ┌─────────────────────────┘
                          ▼
                  ┌───────────────┐
                  │  401 响应      │────>  auth.logout()
                  │  拦截器捕获    │────>  router.push(/login)
                  └───────────────┘
```

- `localStorage` 持久化 token（`auth.ts` store 初始化时恢复）
- 请求时从 Pinia store 读取，而非每次读 localStorage
- 401 响应清除 token 并跳转登录页

### 8.2 会话轮询数据流

```
POST /sessions
  → 存入 sessionId (localStorage + Pinia)
  → 启动 setInterval(3000)
     → GET /sessions/:id
     → 更新 Pinia store → Vue 响应式更新 UI
     → 检测 terminal 状态 → 停止轮询 → 跳转账单
```

- 轮询在组件 `onUnmounted` 时清除
- 页面刷新时从 localStorage 恢复 sessionId，重新开始轮询
- 使用指数退避策略：连续错误时 3s → 5s → 10s → 30s（上限）

### 8.3 充电进度实时更新流

```
后端调度循环 (每 10s)
  → 推进充电电量
  → DB 更新
  → 前端下次轮询 GET /sessions/:id
  → 显示新电量 + 新费用
```

- 无 WebSocket，完全基于轮询
- `currentFee` 在每次轮询响应中携带，前端直接覆盖更新
- 进度百分比前端计算：`chargedEnergy / requestedEnergy * 100`

### 8.4 页面状态矩阵

每个页面/组件必须处理以下四种状态：

| 状态 | 表现 |
|------|------|
| **Loading** | Skeleton 骨架屏（`el-skeleton`），无圆形 spinner |
| **Empty** | EmptyState 组件：图标 + 引导文案 + 操作按钮 |
| **Error** | `ElAlert` 顶部错误提示 + 重试按钮（网络错误可自动重试） |
| **Success** | 正常数据渲染 |

---

## 9. Motion & Interaction

### 9.1 过渡动效

| 场景 | 动效 | 持续时间 |
|------|------|----------|
| 页面切换 | `<router-view>` fade-slide | 200ms ease |
| 状态标签变化 | 背景色 transition | 300ms ease |
| 进度条更新 | width transition | 500ms ease-out |
| 金额数字变化 | 数字滚动效果（`vue-countup`） | 600ms ease-out |
| 轮询数据刷新 | `opacity: 0.6 → 1` 微闪烁 | 200ms |
| 取消/完成状态 | 图标弹跳（bounce-in） | 400ms spring |

### 9.2 微交互

- **排队位置变化时**：位置数字短暂高亮（背景色闪蓝 500ms）
- **充电状态变更时**：顶部 `ElNotification` 弹出提示（如"已进入等待区"）
- **费用更新时**：金额数字颜色从绿色渐变为橙色，吸引注意
- **即将轮到时**：排队位置卡片显示脉冲动画（绿色呼吸圆点，1200ms 循环）

### 9.3 性能规则

- 所有动效仅使用 `transform` 和 `opacity`，禁止动画 `width` / `height` / `top`
- 轮询 interval 在页面隐藏时（`document.hidden`）暂停，恢复时立即执行一次
- 无限循环微动效仅限排队"即将轮到你"脉冲场景，不超过 3 处

---

## 10. Anti-Patterns (Banned)

### 10.1 视觉禁止

- ❌ 禁止 Emoji — 全部使用 Element Plus 图标
- ❌ 禁止纯黑色 `#000000` — 使用 `#1A1A1A`
- ❌ 禁止霓虹/外发光阴影
- ❌ 禁止过度渐变文字（简单的双色渐变可接受，不超过 2 个节点）
- ❌ 禁止自定义鼠标指针样式
- ❌ 禁止等高三栏卡片布局 — 使用 2 列或不对称网格
- ❌ 禁止全屏居中旋转加载图标 — 使用骨架屏

### 10.2 文案禁止

- ❌ 禁止"您已进入排队区，请耐心等待"类虚假友好文案 — 只说事实
- ❌ 禁止英文占位假人名（"John Doe"、"Test User"）
- ❌ 禁止 `99.99%` 类假精准数字
- ❌ 禁止 AI 套话（"Seamless"、"Elevate"、"Next-Gen"）
- ❌ 禁止"Scroll to explore"、"向下滑动"等引导文字

### 10.3 交互禁止

- ❌ 禁止提交按钮无 loading 态 — 所有表单提交必须防重复点击
- ❌ 禁止轮询无限增长 — session 结束后必须停止
- ❌ 禁止路由懒加载无过渡 — 使用 `defineAsyncComponent` 时保留骨架占位
- ❌ 禁止直接修改 Pinia store 的 `$state` 外的深层嵌套 — 使用 `storeToRefs`
- ❌ 禁止在组件内直接使用 `localStorage` — 全部通过 Pinia store 统一管理

### 10.4 数据展示禁止

- ❌ 禁止前端计算费用 — 全部使用 API 返回的 `currentFee`
- ❌ 禁止硬编码状态文本 — 使用 `constants.ts` 枚举映射
- ❌ 禁止金额数字不对齐 — 等宽字体 + `text-align: right`
- ❌ 禁止时间显示无时区信息 — 统一 ISO 8601 + 前端转本地

---

## 11. Constants & Enums

```typescript
// utils/constants.ts

export const SESSION_STATUS = {
  queued:    { label: '排队中',   color: '#2563EB', icon: 'Clock' },
  waiting:  { label: '等待中',   color: '#3B82F6', icon: 'Time' },
  charging: { label: '充电中',   color: '#16A34A', icon: 'Lightning' },
  completed:{ label: '已完成',   color: '#6B7280', icon: 'CircleCheck' },
  cancelled:{ label: '已取消',   color: '#9CA3AF', icon: 'CircleClose' },
} as const

export const STATION_STATUS = {
  running:  { label: '运行中', color: '#16A34A', dot: 'solid' },
  stopping: { label: '停止中', color: '#D97706', dot: 'outline' },
  stopped:  { label: '已停止', color: '#6B7280', dot: 'solid' },
  error:    { label: '异常',   color: '#DC2626', dot: 'exclamation' },
} as const

export const PAYMENT_STATUS = {
  unpaid: { label: '未支付', color: '#D97706' },
  paid:   { label: '已支付', color: '#15803D' },
} as const

export const POLLING_INTERVAL = 3000       // 3 秒
export const POLLING_MAX_BACKOFF = 30000   // 30 秒上限
export const CONFIRM_TIMEOUT = 60          // 充电确认倒计时秒数

export const ZONE_LABELS = {
  queue:    '排队区',
  waiting:  '等待区',
  charging: '充电区',
} as const
```

---

## 12. File Naming & Coding Conventions

### 12.1 命名规则

| 类型 | 规则 | 示例 |
|------|------|------|
| **Vue 组件** | PascalCase | `ChargingStatusBadge.vue` |
| **View 页面** | PascalCase + `View` 后缀 | `LoginView.vue` |
| **API 模块** | camelCase | `station.ts`, `session.ts` |
| **Pinia Store** | camelCase | `auth.ts`, `station.ts` |
| **工具函数** | camelCase | `format.ts`, `polling.ts` |
| **CSS 类名** | kebab-case | `.charging-status-badge` |
| **路由 path** | kebab-case | `/station-detail/:id` |

### 12.2 Vue 组件规范

- 使用 `<script setup lang="ts">` 语法
- Props 使用 `withDefaults` + 类型定义
- Emits 使用 `defineEmits<{...}>()` 类型化
- 组件内状态使用 `ref()` / `computed()`，全局状态使用 Pinia `storeToRefs()`
- 禁止 `this` 关键字

---

> **文档版本**：v1.0 | 2026-06-11
> **适用阶段**：纯后端 API 开发期 — 本规范为前端开发就绪后的统一设计标准。当前所有接口通过 Swagger (`/docs`) 测试验证。
