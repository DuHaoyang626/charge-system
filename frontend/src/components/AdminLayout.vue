<template>
  <div class="admin-layout">
    <!-- 侧边栏遮罩（移动端） -->
    <transition name="fade">
      <div v-if="showSidebar && isMobile" class="sidebar-overlay" @click="showSidebar = false"></div>
    </transition>

    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: !showSidebar, mobile: isMobile }">
      <div class="sidebar-header">
        <span class="sidebar-title">⚡ 管理后台</span>
        <button v-if="isMobile" class="sidebar-close" @click="showSidebar = false">✕</button>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="sidebar-menu"
        background-color="transparent"
        text-color="#CBD5E1"
        active-text-color="#FFFFFF"
        @select="onMenuSelect"
      >
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/admin/stations">
          <el-icon><Monitor /></el-icon>
          <span>充电桩管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/sessions">
          <el-icon><List /></el-icon>
          <span>会话管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/bills">
          <el-icon><Ticket /></el-icon>
          <span>账单管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/queues">
          <el-icon><Sort /></el-icon>
          <span>队列管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/schedule-logs">
          <el-icon><List /></el-icon>
          <span>调度日志</span>
        </el-menu-item>
        <el-menu-item index="/admin/config">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
        <el-menu-item index="/admin/reports">
          <el-icon><TrendCharts /></el-icon>
          <span>数据报表</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <button class="sidebar-theme-btn" @click="toggleTheme">
          <span v-if="isDark">☀️ 明亮模式</span>
          <span v-else>🌙 暗色模式</span>
        </button>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="main-area">
      <header class="admin-topbar glass-navbar">
        <div class="topbar-left">
          <button class="mobile-menu-btn show-mobile touch-target" @click="showSidebar = !showSidebar">
            ☰
          </button>
          <span class="current-page hide-mobile">{{ currentPageName }}</span>
        </div>
        <div class="topbar-right">
          <span class="admin-name hide-xs">{{ user?.userName || '管理员' }}</span>
          <el-tag size="small" type="danger" effect="dark" class="hide-xs">管理员</el-tag>
          <button class="btn-glass btn-glass-sm" @click="goToUserHome">
            <span class="hide-xs">用户端</span>
            <span class="show-mobile">🏠</span>
          </button>
          <button class="btn-glass btn-glass-sm hide-xs" @click="handleLogout">退出</button>
        </div>
      </header>

      <main class="admin-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  DataAnalysis, Monitor, List, Ticket, Sort,
  Setting, TrendCharts,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const user = computed(() => auth.user)
const { toggleTheme, isDark } = useTheme()
const showSidebar = ref(true)
const isMobile = ref(false)

const pageNames: Record<string, string> = {
  '/admin/dashboard': '仪表盘',
  '/admin/stations': '充电桩管理',
  '/admin/sessions': '会话管理',
  '/admin/bills': '账单管理',
  '/admin/queues': '队列管理',
  '/admin/schedule-logs': '调度日志',
  '/admin/config': '系统配置',
  '/admin/reports': '数据报表',
}

const currentPageName = computed(() => pageNames[route.path] || '管理后台')

function checkMobile() {
  isMobile.value = window.innerWidth < 769
  if (isMobile.value) showSidebar.value = false
  else showSidebar.value = true
}

function onMenuSelect() {
  if (isMobile.value) showSidebar.value = false
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出管理后台吗？', '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    })
    auth.logout()
    router.push('/admin/login')
  } catch { /* cancel */ }
}

function goToUserHome() {
  router.push('/')
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.admin-layout {
  display: flex;
  height: 100dvh;
  background: var(--bg-primary);
  position: relative;
}

/* 侧边栏遮罩 */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 199;
}

/* 侧边栏 */
.sidebar {
  width: 220px;
  min-width: 220px;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  border-right: 1px solid rgba(255,255,255,0.06);
  z-index: 200;
}

.sidebar.mobile {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  transform: translateX(-100%);
  z-index: 200;
  box-shadow: 4px 0 20px rgba(0,0,0,0.3);
}

.sidebar.mobile.collapsed {
  transform: translateX(0);
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.sidebar-title {
  font-size: 17px;
  font-weight: 700;
  color: #FFFFFF;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.sidebar-close {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255,255,255,0.1);
  color: #CBD5E1;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  padding: 8px 0;
  overflow-y: auto;
}

.sidebar-menu .el-menu-item {
  margin: 2px 8px;
  border-radius: 8px;
  transition: all 0.2s ease;
  min-height: 40px;
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255,255,255,0.08) !important;
}

.sidebar-menu .el-menu-item.is-active {
  background: var(--color-primary) !important;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.sidebar-theme-btn {
  width: 100%;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.04);
  color: #CBD5E1;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sidebar-theme-btn:hover {
  background: rgba(255,255,255,0.10);
  color: #FFFFFF;
}

/* 主区域 */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.admin-topbar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 clamp(12px, 2vw, 20px);
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.current-page {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.mobile-menu-btn {
  width: 36px;
  height: 36px;
  border: var(--glass-border);
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

.topbar-right {
  display: flex;
  align-items: center;
  gap: clamp(6px, 1vw, 12px);
}

.admin-name {
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: clamp(12px, 2vw, 24px);
  -webkit-overflow-scrolling: touch;
}

/* fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (min-width: 769px) {
  .sidebar.mobile {
    position: static;
    transform: none !important;
  }
}
</style>
