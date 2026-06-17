/**
 * 认证状态管理 (Pinia)
 * 管理 JWT Token、用户信息、登录/登出
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo, LoginRequest, RegisterRequest, LoginResponse, RegisterResponse } from '@/api/auth'
import { loginApi, registerApi, getUserInfoApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // ── State ──
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<UserInfo | null>(_loadUser())
  const userRole = ref<string | null>(localStorage.getItem('userRole'))
  const loading = ref(false)

  // ── Getters ──
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userRole.value === 'admin')
  const activeSession = computed(() => user.value?.activeSession ?? null)

  // ── Actions ──

  /** 登录 */
  async function login(data: LoginRequest) {
    loading.value = true
    try {
      const res = await loginApi(data)
      const body = res.data as { code: number; data: LoginResponse; message?: string }
      if (body.code === 200) {
        _setSession(body.data)
        return body.data
      }
      throw new Error(body.message || (res.data as any)?.message || '登录失败')
    } finally {
      loading.value = false
    }
  }

  /** 注册 */
  async function register(data: RegisterRequest) {
    loading.value = true
    try {
      const res = await registerApi(data)
      const body = res.data as { code: number; data: RegisterResponse; message: string }
      if (body.code === 201) {
        _setSession({ ...body.data, role: 'user' } as LoginResponse)
        return body.data
      }
      throw new Error(body.message || '注册失败')
    } finally {
      loading.value = false
    }
  }

  /** 获取用户信息 */
  async function fetchUserInfo() {
    try {
      const res = await getUserInfoApi()
      const body = res.data as { code: number; data: UserInfo }
      if (body.code === 200) {
        user.value = body.data
        localStorage.setItem('user', JSON.stringify(body.data))
        return body.data
      }
    } catch {
      // 静默失败（路由守卫会处理 401）
    }
    return null
  }

  /** 登出 */
  function logout() {
    token.value = null
    user.value = null
    userRole.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('userRole')
  }

  /** 从登录/注册响应恢复 session */
  function _setSession(data: LoginResponse | (RegisterResponse & { role: string })) {
    token.value = data.token
    localStorage.setItem('token', data.token)
    if ('role' in data) {
      userRole.value = data.role
      localStorage.setItem('userRole', data.role)
    }
    // 立即获取用户信息
    fetchUserInfo()
  }

  function _loadUser(): UserInfo | null {
    try {
      const raw = localStorage.getItem('user')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  }

  return {
    token,
    user,
    loading,
    isLoggedIn,
    isAdmin,
    activeSession,
    login,
    register,
    fetchUserInfo,
    logout,
  }
})
