<template>
  <div class="app-layout">
    <!-- 顶栏 -->
    <header class="top-bar">
      <div class="top-bar-left">
        <span class="system-title">⚡ 智能充电桩</span>
        <el-menu mode="horizontal" :ellipsis="false" class="nav-menu" router :default-active="route.path">
          <el-menu-item index="/">主页</el-menu-item>
          <el-menu-item index="/stations">充电桩</el-menu-item>
          <el-menu-item index="/bills">账单</el-menu-item>
        </el-menu>
      </div>
      <div class="top-bar-right">
        <template v-if="user">
          <span class="user-name">{{ user.userName }}</span>
          <el-tag size="small" :type="isAdmin ? 'danger' : 'primary'" effect="plain">
            {{ user.licensePlate }}
          </el-tag>
          <el-button v-if="isAdmin" text size="small" @click="goToAdmin" type="danger">
            管理后台
          </el-button>
          <el-button text size="small" @click="handleLogout">退出</el-button>
        </template>
      </div>
    </header>

    <!-- 内容区 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const user = computed(() => auth.user)
const isAdmin = computed(() => auth.isAdmin)

function goToAdmin() {
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
  height: 56px;
  background: #FFFFFF;
  border-bottom: 1px solid rgba(209, 213, 219, 0.6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.system-title {
  font-size: 18px;
  font-weight: 600;
  color: #1A1A1A;
  margin-right: 8px;
}

/* 顶栏导航菜单 */
.nav-menu {
  border-bottom: none !important;
  background: transparent;
}

.nav-menu .el-menu-item {
  font-size: 14px;
  height: 56px;
  line-height: 56px;
  border-bottom: 2px solid transparent;
}

.nav-menu .el-menu-item.is-active {
  border-bottom-color: #2563EB;
  color: #2563EB;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  font-size: 14px;
  color: #737373;
}

.main-content {
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: 24px;
}
</style>
