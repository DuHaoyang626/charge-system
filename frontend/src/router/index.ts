/**
 * Vue Router 配置
 * - 路由表定义
 * - 导航守卫（登录校验 / 管理员校验）
 */

import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // ── 认证页（无布局壳） ──
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/auth/RegisterView.vue'),
      meta: { guest: true },
    },
    {
      path: '/admin/login',
      name: 'AdminLogin',
      component: () => import('@/views/admin/AdminLoginView.vue'),
      meta: { guest: true },
    },

    // ── 用户端（AppLayout 壳） ──
    {
      path: '/',
      component: () => import('@/components/AppLayout.vue'),
      meta: { auth: true },
      children: [
        {
          path: '',
          name: 'Home',
          component: () => import('@/views/home/HomeView.vue'),
        },
        {
          path: 'stations',
          name: 'StationList',
          component: () => import('@/views/station/StationListView.vue'),
        },
        {
          path: 'stations/:id',
          name: 'StationDetail',
          component: () => import('@/views/station/StationDetailView.vue'),
        },
        {
          path: 'sessions/create',
          name: 'SessionCreate',
          component: () => import('@/views/session/SessionCreateView.vue'),
        },
        {
          path: 'sessions/:id',
          name: 'SessionProgress',
          component: () => import('@/views/session/SessionProgressView.vue'),
        },
        {
          path: 'bills',
          name: 'BillsList',
          component: () => import('@/views/bill/BillsListView.vue'),
        },
        {
          path: 'bills/:id',
          name: 'BillDetail',
          component: () => import('@/views/bill/BillDetailView.vue'),
        },
      ],
    },

    // ── 管理端（AdminLayout 壳，需 admin 权限） ──
    {
      path: '/admin',
      component: () => import('@/components/AdminLayout.vue'),
      meta: { auth: true, admin: true },
      children: [
        {
          path: 'dashboard',
          name: 'AdminDashboard',
          component: () => import('@/views/admin/DashboardView.vue'),
        },
        {
          path: 'stations',
          name: 'AdminStations',
          component: () => import('@/views/admin/StationManageView.vue'),
        },
        {
          path: 'sessions',
          name: 'AdminSessions',
          component: () => import('@/views/admin/SessionManageView.vue'),
        },
        {
          path: 'bills',
          name: 'AdminBills',
          component: () => import('@/views/admin/BillManageView.vue'),
        },
        {
          path: 'queues',
          name: 'AdminQueues',
          component: () => import('@/views/admin/QueueManageView.vue'),
        },
        {
          path: 'config',
          name: 'AdminConfig',
          component: () => import('@/views/admin/ConfigView.vue'),
        },
        {
          path: 'reports',
          name: 'AdminReports',
          component: () => import('@/views/admin/ReportView.vue'),
        },
      ],
    },

    // ── 未匹配 → 登录页 ──
    {
      path: '/:pathMatch(.*)*',
      redirect: '/login',
    },
  ],
})

// ── 导航守卫 ──

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('userRole')

  // 已登录访问登录/注册页 → 跳转对应主页
  if (to.meta.guest && token) {
    if (to.path.startsWith('/admin') && role === 'admin') {
      return next('/admin/dashboard')
    }
    if (!to.path.startsWith('/admin')) {
      return next('/')
    }
  }

  // 需要登录但没有 token → 跳转对应登录页
  if (to.meta.auth && !token) {
    if (to.path.startsWith('/admin')) {
      ElMessage.warning('请先登录管理后台')
      return next('/admin/login')
    }
    ElMessage.warning('请先登录')
    return next('/login')
  }

  // 管理端路由需要 admin 角色
  if (to.meta.admin && role !== 'admin') {
    ElMessage.error('无权访问管理后台')
    return next('/')
  }

  next()
})

// Element Plus Message 用于守卫提示
import { ElMessage } from 'element-plus'

export default router
