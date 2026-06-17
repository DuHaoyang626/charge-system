<template>
  <div class="app-layout glass-container">
    <!-- 顶栏 -->
    <header class="top-bar glass-navbar">
      <div class="top-bar-left">
        <button class="mobile-menu-btn show-mobile" @click="mobileMenuOpen = !mobileMenuOpen">
          <span v-if="mobileMenuOpen">✕</span>
          <span v-else>☰</span>
        </button>
        <span class="system-title">⚡ 智能充电桩</span>
        <el-menu mode="horizontal" :ellipsis="false" class="nav-menu hide-mobile" router :default-active="route.path">
          <el-menu-item index="/">主页</el-menu-item>
          <el-menu-item index="/stations">充电桩</el-menu-item>
          <el-menu-item index="/bills">账单</el-menu-item>
        </el-menu>
      </div>
      <div class="top-bar-right">
        <button class="theme-toggle-btn touch-target" @click="toggleTheme" :title="isDark ? '切换到明亮模式' : '切换到暗色模式'">
          <span v-if="isDark">☀️</span>
          <span v-else>🌙</span>
        </button>
        <template v-if="user">
          <span class="user-name hide-xs">{{ user.userName }}</span>
          <el-tag size="small" :type="isAdmin ? 'danger' : 'primary'" effect="plain" class="hide-xs">
            {{ user.licensePlate }}
          </el-tag>
          <button v-if="isAdmin" class="btn-glass btn-glass-sm" @click="goToAdmin" style="color: var(--color-danger);">
            <span class="hide-xs">管理后台</span>
            <span class="show-mobile">🔐</span>
          </button>
          <button class="btn-glass btn-glass-sm hide-xs" @click="handleLogout">退出</button>
        </template>
      </div>
    </header>

    <!-- 移动端下拉菜单 -->
    <transition name="slide-down">
      <div v-if="mobileMenuOpen" class="mobile-nav glass-card-strong">
        <router-link to="/" class="mobile-nav-item" @click="mobileMenuOpen = false" :class="{ active: route.path === '/' }">
          🏠 主页
        </router-link>
        <router-link to="/stations" class="mobile-nav-item" @click="mobileMenuOpen = false" :class="{ active: route.path.startsWith('/stations') }">
          🔌 充电桩
        </router-link>
        <router-link to="/bills" class="mobile-nav-item" @click="mobileMenuOpen = false" :class="{ active: route.path.startsWith('/bills') }">
          📋 账单
        </router-link>
        <template v-if="user">
          <div class="mobile-nav-divider"></div>
          <span class="mobile-nav-user">{{ user.userName }} · {{ user.licensePlate }}</span>
          <button class="mobile-nav-logout" @click="handleLogout">退出登录</button>
        </template>
      </div>
    </transition>

    <!-- 内容区 -->
    <main class="main-content page-enter" @click="mobileMenuOpen = false">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const user = computed(() => auth.user)
const isAdmin = computed(() => auth.isAdmin)
const { toggleTheme, isDark } = useTheme()
const mobileMenuOpen = ref(false)

function goToAdmin() {
  mobileMenuOpen.value = false
  router.push('/admin/dashboard')
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    auth.logout()
    router.push('/login')
  } catch {
    // 取消操作
  }
}
</script>

<style scoped>
.app-layout {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}

.top-bar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 clamp(12px, 2vw, 28px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: clamp(4px, 1vw, 12px);
  min-width: 0;
}

.system-title {
  font-size: clamp(16px, 2vw, 18px);
  font-weight: 700;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  white-space: nowrap;
}

.mobile-menu-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: var(--bg-glass);
  backdrop-filter: var(--glass-blur);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-menu {
  border-bottom: none !important;
  background: transparent;
}

.nav-menu .el-menu-item {
  font-size: 14px;
  height: 60px;
  line-height: 60px;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
}

.nav-menu .el-menu-item.is-active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 600;
}

.nav-menu .el-menu-item:hover {
  color: var(--color-primary) !important;
  background: transparent !important;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: clamp(6px, 1vw, 12px);
}

.user-name {
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.theme-toggle-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: var(--glass-border);
  background: var(--bg-glass);
  backdrop-filter: var(--glass-blur);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.3s ease;
  padding: 0;
}

.theme-toggle-btn:hover {
  background: var(--bg-glass-hover);
  transform: scale(1.1);
}

/* 移动端导航 */
.mobile-nav {
  position: fixed;
  top: 60px;
  left: 0;
  right: 0;
  z-index: 99;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  border-top: none;
  max-height: calc(100dvh - 60px);
  overflow-y: auto;
}

.mobile-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.2s;
}

.mobile-nav-item:active,
.mobile-nav-item.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.mobile-nav-divider {
  height: 1px;
  background: var(--border-light);
  margin: 8px 0;
}

.mobile-nav-user {
  padding: 8px 16px 4px;
  font-size: 13px;
  color: var(--text-tertiary);
}

.mobile-nav-logout {
  padding: 14px 16px;
  border: none;
  background: none;
  color: var(--color-danger);
  font-size: 15px;
  text-align: left;
  border-radius: var(--radius-md);
  cursor: pointer;
}

/* slide-down 动画 */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.slide-down-enter-from,
.slide-down-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.main-content {
  flex: 1;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: clamp(16px, 2.5vw, 28px) clamp(12px, 2vw, 24px);
}

@media (max-width: 480px) {
  .main-content {
    padding: 12px;
  }
}
</style>
