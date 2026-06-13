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
        // 后续页面在此扩展
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

  // 已登录访问登录/注册页 → 跳转主页
  if (to.meta.guest && token) {
    return next('/')
  }

  // 需要登录但没有 token → 跳转登录
  if (to.meta.auth && !token) {
    ElMessage.warning('请先登录')
    return next('/login')
  }

  next()
})

// Element Plus Message 用于守卫提示
import { ElMessage } from 'element-plus'

export default router
