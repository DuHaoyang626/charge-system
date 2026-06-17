<template>
  <div class="home">
    <!-- 用户信息卡片 + 快捷操作 -->
    <div class="hero-section">
      <div class="glass-card user-card">
        <div class="user-info">
          <div class="user-avatar glass-card-strong">
            <el-icon :size="clampIcon(24, 32)" color="var(--color-primary)">
              <User />
            </el-icon>
          </div>
          <div class="user-detail">
            <h3>{{ user?.userName }}</h3>
            <p class="user-meta">
              <el-tag size="small" type="primary" effect="plain">{{ user?.licensePlate }}</el-tag>
              <span class="meta-item">🔋 {{ user?.batteryCapacity }} kWh</span>
            </p>
            <div class="protocol-tags" v-if="user?.protocols?.length">
              <span class="meta-label">支持协议：</span>
              <el-tag
                v-for="p in user!.protocols"
                :key="p.id"
                size="small"
                effect="plain"
                class="glass-badge"
              >{{ p.name }}</el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 快捷操作 -->
      <div class="quick-actions">
        <button class="btn-glass btn-glass-primary btn-glass-lg quick-btn" @click="goToCreate">
          ⚡ 发起充电
        </button>
        <button class="btn-glass btn-glass-lg quick-btn" @click="goToBills">
          📋 历史账单
        </button>
        <button v-if="isAdmin" class="btn-glass btn-glass-danger btn-glass-lg quick-btn" @click="goToAdmin">
          🔐 管理后台
        </button>
      </div>
    </div>

    <!-- 活动会话卡片 -->
    <template v-if="activeSession">
      <div class="glass-card session-card" @click="goToSession" style="cursor: pointer;">
        <div class="session-header">
          <ChargingStatusBadge :status="activeSession.status" />
          <span class="session-station">{{ activeSession.stationName }}</span>
          <span class="tap-hint hide-xs">点击查看详情 →</span>
        </div>
        <div class="session-body">
          <el-progress
            type="circle"
            :percentage="activeSession.progress"
            :color="progressColor"
            :width="clampNum(60, 80)"
            :stroke-width="6"
          />
          <div class="session-info">
            <p class="session-status-text">
              {{ activeSession.status === 'charging' ? '⚡ 充电中' : '⏳ 排队中' }}
            </p>
            <p class="session-pct">{{ activeSession.progress }}%</p>
            <p class="info-text">{{ activeSession.stationName }}</p>
          </div>
        </div>
        <div class="session-footer show-mobile">
          <span class="tap-hint">点击查看详情 →</span>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="glass-card session-card empty-card">
        <EmptyState description="暂无进行中的充电会话" action-text="⚡ 发起充电" @action="goToCreate" />
      </div>
    </template>

    <!-- 充电桩 Dashboard -->
    <section class="dashboard-section">
      <div class="section-header">
        <h2>🔌 充电桩状态</h2>
        <button class="btn-glass btn-glass-sm" @click="refreshStations" :disabled="loading">
          {{ loading ? '⟳' : '⟳ 刷新' }}
        </button>
      </div>

      <div v-if="loading && stations.length === 0" class="loading-skeleton">
        <el-skeleton :rows="3" animated />
      </div>

      <div v-else class="responsive-grid">
        <div
          v-for="s in stations"
          :key="s.id"
          class="glass-card station-card"
          :class="{ 'is-disabled': s.status !== 'running' }"
          @click="goToDetail(s.id)"
        >
          <div class="card-header">
            <div class="card-title-row">
              <h3>{{ s.name }}</h3>
              <StationStatusBadge :status="s.status" />
            </div>
            <span v-if="s.status === 'running'" class="wait-time glass-badge">
              ⏱ ~{{ s.estimatedWaitMinutes }}分
            </span>
          </div>

          <div class="zone-bars">
            <div class="zone-item">
              <span class="zone-label">🚶</span>
              <el-progress
                :percentage="capacityPct(s.queueCount, s.queueCapacity)"
                :stroke-width="8"
                color="#3B82F6"
                :format="() => `${s.queueCount}/${s.queueCapacity}`"
              />
            </div>
            <div class="zone-item">
              <span class="zone-label">⏳</span>
              <el-progress
                :percentage="capacityPct(s.waitingCount, s.waitingCapacity)"
                :stroke-width="8"
                color="#F59E0B"
                :format="() => `${s.waitingCount}/${s.waitingCapacity}`"
              />
            </div>
            <div class="zone-item">
              <span class="zone-label">⚡</span>
              <el-progress
                :percentage="capacityPct(s.chargingCount, s.chargingCapacity)"
                :stroke-width="8"
                color="#22C55E"
                :format="() => `${s.chargingCount}/${s.chargingCapacity}`"
              />
            </div>
          </div>

          <div class="protocol-tags">
            <el-tag
              v-for="p in s.supportedProtocols"
              :key="p.id"
              size="small"
              effect="plain"
              class="glass-badge"
            >{{ p.name }}</el-tag>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useStationStore } from '@/stores/station'
import ChargingStatusBadge from '@/components/ChargingStatusBadge.vue'
import StationStatusBadge from '@/components/StationStatusBadge.vue'
import EmptyState from '@/components/EmptyState.vue'
import { POLLING_INTERVAL } from '@/utils/constants'

const router = useRouter()
const auth = useAuthStore()
const stationStore = useStationStore()

const user = computed(() => auth.user)
const activeSession = computed(() => auth.activeSession)
const stations = computed(() => stationStore.stations)
const loading = computed(() => stationStore.loading)
const isAdmin = computed(() => auth.isAdmin)

let pollingTimer: ReturnType<typeof setInterval> | null = null

function startPolling() {
  stopPolling()
  pollingTimer = setInterval(() => {
    stationStore.fetchStations(true)
    if (auth.user) auth.fetchUserInfo()
  }, POLLING_INTERVAL)
}
function stopPolling() {
  if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null }
}

const progressColor = computed(() => {
  if (!activeSession.value) return 'var(--color-primary)'
  return activeSession.value.status === 'charging' ? 'var(--color-success)' : 'var(--color-primary)'
})

function capacityPct(count: number, capacity: number): number {
  if (capacity <= 0) return 0
  return Math.min(100, Math.round((count / capacity) * 100))
}

function clampIcon(min: number, max: number) {
  return Math.max(min, Math.min(max, Math.round(window.innerWidth / 25)))
}

function clampNum(min: number, max: number) {
  return Math.max(min, Math.min(max, Math.round(window.innerWidth / 12)))
}

function goToSession() { activeSession.value && router.push(`/sessions/${activeSession.value.sessionId}`) }
function goToCreate() { router.push('/sessions/create') }
function goToDetail(id: number) { router.push(`/stations/${id}`) }
function goToBills() { router.push('/bills') }
function goToAdmin() { router.push('/admin/dashboard') }
function refreshStations() { stationStore.fetchStations() }

onMounted(async () => {
  if (!auth.user) await auth.fetchUserInfo()
  stationStore.fetchStations()
  startPolling()
})
onUnmounted(stopPolling)
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: clamp(16px, 2vw, 24px);
  max-width: 1200px;
  margin: 0 auto;
}

.hero-section {
  display: flex;
  flex-direction: column;
  gap: clamp(12px, 1.5vw, 16px);
}

.user-card {
  padding: clamp(16px, 2vw, 24px);
}

.user-info {
  display: flex;
  align-items: flex-start;
  gap: clamp(12px, 1.5vw, 16px);
}

.user-avatar {
  width: clamp(44px, 5vw, 56px);
  height: clamp(44px, 5vw, 56px);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-detail h3 {
  font-size: clamp(16px, 2vw, 18px);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.user-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.meta-item {
  font-size: 13px;
  color: var(--text-tertiary);
}

.meta-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.protocol-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* 快捷操作 */
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: clamp(8px, 1vw, 12px);
}

.quick-btn {
  flex: 1;
  min-width: 140px;
}

@media (max-width: 480px) {
  .quick-btn {
    min-width: calc(50% - 6px);
    flex: 1 1 auto;
  }
}

/* 会话卡片 */
.session-card {
  padding: clamp(16px, 2vw, 24px);
  transition: all 0.3s ease;
}

.session-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), var(--shadow-glass);
}

.session-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: clamp(12px, 1.5vw, 16px);
  flex-wrap: wrap;
}

.session-station {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
}

.session-body {
  display: flex;
  align-items: center;
  gap: clamp(16px, 2.5vw, 24px);
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-status-text {
  font-size: clamp(14px, 1.5vw, 16px);
  font-weight: 600;
  color: var(--color-success);
}

.session-pct {
  font-size: clamp(22px, 3vw, 28px);
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
}

.info-text {
  font-size: 13px;
  color: var(--text-tertiary);
}

.tap-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

.session-footer {
  text-align: right;
  margin-top: 8px;
}

.empty-card {
  display: flex;
  justify-content: center;
}

/* 充电桩区域 */
.dashboard-section {
  display: flex;
  flex-direction: column;
  gap: clamp(12px, 1.5vw, 16px);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h2 {
  font-size: clamp(17px, 2vw, 20px);
  font-weight: 600;
  color: var(--text-primary);
}

.station-card {
  padding: clamp(14px, 1.8vw, 20px);
  cursor: pointer;
  transition: all 0.3s ease;
}

.station-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), var(--shadow-glass);
}

.station-card.is-disabled {
  opacity: 0.6;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: clamp(10px, 1.2vw, 14px);
  gap: 8px;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.card-title-row h3 {
  font-size: clamp(14px, 1.4vw, 16px);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wait-time {
  font-size: clamp(11px, 1vw, 12px);
  white-space: nowrap;
}

.zone-bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: clamp(10px, 1.2vw, 14px);
}

.zone-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.zone-label {
  font-size: clamp(12px, 1.2vw, 14px);
  width: 24px;
  flex-shrink: 0;
  text-align: center;
}

.zone-item .el-progress {
  flex: 1;
}

.protocol-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.loading-skeleton {
  padding: 24px 0;
}
</style>
