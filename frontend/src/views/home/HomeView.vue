<template>
  <div class="home">
    <!-- 用户信息卡片 -->
    <el-card shadow="never" class="user-card">
      <div class="user-info">
        <div class="user-avatar">
          <el-icon :size="32" color="#FFFFFF">
            <User />
          </el-icon>
        </div>
        <div class="user-detail">
          <h3>{{ user?.userName }}</h3>
          <p class="user-meta">
            <el-tag size="small" type="primary" effect="plain">{{ user?.licensePlate }}</el-tag>
            <span class="meta-item">电池容量 {{ user?.batteryCapacity }} kWh</span>
          </p>
          <div class="protocol-tags" v-if="user?.protocols?.length">
            <span class="meta-label">支持协议：</span>
            <el-tag
              v-for="p in user!.protocols"
              :key="p.id"
              size="small"
              effect="plain"
              :color="'#DBEAFE'"
              style="border: none; color: #1E40AF;"
            >
              {{ p.name }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 活动会话卡片 -->
    <el-card
      v-if="activeSession"
      shadow="never"
      class="active-session-card"
      @click="goToSession"
      style="cursor: pointer;"
    >
      <div class="session-header">
        <ChargingStatusBadge :status="activeSession.status" />
        <span class="session-station">{{ activeSession.stationName }}</span>
      </div>
      <div class="session-body">
        <div class="progress-section">
          <el-progress
            type="circle"
            :percentage="activeSession.progress"
            :color="progressColor"
            :width="80"
            :stroke-width="6"
          />
          <div class="progress-label">
            <p class="progress-text">{{ activeSession.status === 'charging' ? '充电中' : '排队中' }}</p>
            <p class="progress-pct">{{ activeSession.progress }}%</p>
          </div>
        </div>
      </div>
      <div class="session-footer">
        <span class="tap-hint">点击查看详情 →</span>
      </div>
    </el-card>

    <!-- 空状态：无活动会话 -->
    <el-card v-else shadow="never" class="empty-card">
      <EmptyState
        icon="Charging"
        description="暂无进行中的充电会话"
        action-text="发起充电"
        @action="goToCreate"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import ChargingStatusBadge from '@/components/ChargingStatusBadge.vue'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()
const auth = useAuthStore()

const user = computed(() => auth.user)
const activeSession = computed(() => auth.activeSession)

const progressColor = computed(() => {
  if (!activeSession.value) return '#2563EB'
  if (activeSession.value.status === 'charging') return '#16A34A'
  return '#2563EB'
})

function goToSession() {
  if (activeSession.value) {
    router.push(`/sessions/${activeSession.value.sessionId}`)
  }
}

function goToCreate() {
  router.push('/sessions/create')
}

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchUserInfo()
  }
})
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 600px;
  margin: 0 auto;
}

/* 用户信息卡片 */
.user-card {
  border-radius: 12px;
}

.user-info {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.user-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #2563EB;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-detail h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1A1A1A;
  margin-bottom: 4px;
}

.user-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.meta-item {
  font-size: 13px;
  color: #737373;
}

.protocol-tags {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.meta-label {
  font-size: 12px;
  color: #737373;
}

/* 活动会话卡片 */
.active-session-card {
  border-radius: 12px;
  border-left: 4px solid #16A34A;
  transition: box-shadow 0.2s;
}

.active-session-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.session-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.session-station {
  font-size: 14px;
  font-weight: 500;
  color: #1A1A1A;
}

.session-body {
  display: flex;
  justify-content: center;
  padding: 8px 0;
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 20px;
}

.progress-label {
  text-align: left;
}

.progress-text {
  font-size: 14px;
  color: #737373;
}

.progress-pct {
  font-size: 24px;
  font-weight: 600;
  color: #1A1A1A;
  font-family: 'JetBrains Mono', monospace;
}

.session-footer {
  text-align: right;
  margin-top: 8px;
}

.tap-hint {
  font-size: 12px;
  color: #9CA3AF;
}

/* 空状态卡片 */
.empty-card {
  border-radius: 12px;
}
</style>
