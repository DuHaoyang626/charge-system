<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed }">
      <div class="sidebar-header">
        <span class="sidebar-title">⚡ 管理后台</span>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="sidebar-menu"
        background-color="#1E293B"
        text-color="#CBD5E1"
        active-text-color="#FFFFFF"
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
        <el-menu-item index="/admin/config">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
        <el-menu-item index="/admin/reports">
          <el-icon><TrendCharts /></el-icon>
          <span>数据报表</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <!-- 主区域 -->
    <div class="main-area">
      <!-- 顶栏 -->
      <header class="admin-topbar">
        <el-button text @click="collapsed = !collapsed">
          <el-icon :size="20"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
        </el-button>
        <div class="topbar-right">
          <span class="admin-name">{{ user?.userName || '管理员' }}</span>
          <el-tag size="small" type="danger" effect="dark">管理员</el-tag>
          <el-button text size="small" @click="goToUserHome">用户端</el-button>
          <el-button text size="small" @click="handleLogout">退出</el-button>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="admin-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  DataAnalysis, Monitor, List, Ticket, Sort,
  Setting, TrendCharts, Fold, Expand,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const collapsed = ref(false)
const user = computed(() => auth.user)

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
</script>

<style scoped>
.admin-layout {
  display: flex;
  height: 100dvh;
  background: #F1F5F9;
}

/* 侧边栏 */
.sidebar {
  width: 220px;
  background: #1E293B;
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
  white-space: nowrap;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
}

/* 主区域 */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.admin-topbar {
  height: 56px;
  background: #FFFFFF;
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-name {
  font-size: 14px;
  color: #475569;
}

.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>
