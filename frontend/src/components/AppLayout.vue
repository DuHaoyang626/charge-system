<template>
  <div class="app-layout">
    <!-- 顶栏 -->
    <header class="top-bar">
      <div class="top-bar-left">
        <span class="system-title">⚡ 智能充电桩</span>
      </div>
      <div class="top-bar-right">
        <template v-if="user">
          <span class="user-name">{{ user.userName }}</span>
          <el-tag size="small" :type="user.licensePlate === 'ADMIN' ? 'danger' : 'primary'" effect="plain">
            {{ user.licensePlate }}
          </el-tag>
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
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()
const user = computed(() => auth.user)

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
