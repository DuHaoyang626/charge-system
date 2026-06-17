<template>
  <div class="station-list">
    <div class="page-header-responsive">
      <div>
        <h2>🔌 充电桩列表</h2>
        <p class="page-desc">共 {{ stations.length }} 个充电桩</p>
      </div>
      <span class="glass-badge hide-xs">共 {{ stations.length }} 个充电桩</span>
    </div>

    <div v-if="loading" class="loading-skeleton">
      <el-skeleton :rows="3" animated />
    </div>
    <div v-else-if="stations.length === 0" class="glass-card" style="padding:0;">
      <EmptyState description="暂无充电桩数据" />
    </div>
    <div v-else class="responsive-grid">
      <div v-for="s in stations" :key="s.id" class="glass-card station-card" :class="{ 'is-disabled': s.status !== 'running' }" @click="goToDetail(s.id)">
        <div class="card-header">
          <div class="card-title-row">
            <h3>{{ s.name }}</h3>
            <StationStatusBadge :status="s.status" />
          </div>
          <span v-if="s.status === 'running'" class="glass-badge wait-time">⏱ ~{{ s.estimatedWaitMinutes }}分</span>
        </div>
        <div class="zone-bars">
          <div class="zone-item">
            <span class="zone-label">🚶</span>
            <el-progress :percentage="capacityPct(s.queueCount, s.queueCapacity)" :stroke-width="8" color="#3B82F6" :format="() => `${s.queueCount}/${s.queueCapacity}`" />
          </div>
          <div class="zone-item">
            <span class="zone-label">⏳</span>
            <el-progress :percentage="capacityPct(s.waitingCount, s.waitingCapacity)" :stroke-width="8" color="#F59E0B" :format="() => `${s.waitingCount}/${s.waitingCapacity}`" />
          </div>
          <div class="zone-item">
            <span class="zone-label">⚡</span>
            <el-progress :percentage="capacityPct(s.chargingCount, s.chargingCapacity)" :stroke-width="8" color="#22C55E" :format="() => `${s.chargingCount}/${s.chargingCapacity}`" />
          </div>
        </div>
        <div class="protocol-tags">
          <el-tag v-for="p in s.supportedProtocols" :key="p.id" size="small" effect="plain" class="glass-badge">{{ p.name }}</el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStationStore } from '@/stores/station'
import StationStatusBadge from '@/components/StationStatusBadge.vue'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()
const store = useStationStore()
const stations = computed(() => store.stations)
const loading = computed(() => store.loading)

function capacityPct(count: number, capacity: number): number {
  if (capacity <= 0) return 0
  return Math.min(100, Math.round((count / capacity) * 100))
}
function goToDetail(id: number) { router.push(`/stations/${id}`) }
onMounted(() => store.fetchStations())
</script>

<style scoped>
.station-list { max-width: 1200px; margin: 0 auto; }
.station-card { padding: clamp(14px, 1.8vw, 20px); cursor: pointer; transition: all 0.3s ease; }
.station-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg), var(--shadow-glass); }
.station-card.is-disabled { opacity: 0.6; }
.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: clamp(10px, 1.2vw, 14px); gap: 8px; }
.card-title-row { display: flex; align-items: center; gap: 8px; min-width: 0; }
.card-title-row h3 { font-size: clamp(14px, 1.4vw, 16px); font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.wait-time { font-size: clamp(11px, 1vw, 12px); white-space: nowrap; }
.zone-bars { display: flex; flex-direction: column; gap: 6px; margin-bottom: clamp(10px, 1.2vw, 14px); }
.zone-item { display: flex; align-items: center; gap: 6px; }
.zone-label { font-size: clamp(12px, 1.2vw, 14px); width: 24px; flex-shrink: 0; text-align: center; }
.zone-item .el-progress { flex: 1; }
.protocol-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.loading-skeleton { padding: 24px 0; }
</style>
