<template>
  <div class="station-list">
    <h2 class="page-title">充电桩列表</h2>

    <div v-if="loading" class="loading-skeleton">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="stations.length === 0" class="empty-wrapper">
      <EmptyState description="暂无充电桩数据" />
    </div>

    <div v-else class="station-grid">
      <el-card
        v-for="s in stations"
        :key="s.id"
        shadow="never"
        class="station-card"
        :class="{ 'is-disabled': s.status !== 'running' }"
        @click="goToDetail(s.id)"
      >
        <div class="card-header">
          <div class="card-title-row">
            <h3>{{ s.name }}</h3>
            <StationStatusBadge :status="s.status" />
          </div>
          <span v-if="s.status === 'running'" class="wait-time">
            约 {{ s.estimatedWaitMinutes }} 分钟
          </span>
        </div>

        <!-- 三区容量条 -->
        <div class="zone-bars">
          <div class="zone-item">
            <span class="zone-label">排队</span>
            <el-progress
              :percentage="capacityPct(s.queueCount, s.queueCapacity)"
              :stroke-width="8"
              color="#2563EB"
              :format="() => `${s.queueCount}/${s.queueCapacity}`"
            />
          </div>
          <div class="zone-item">
            <span class="zone-label">等待</span>
            <el-progress
              :percentage="capacityPct(s.waitingCount, s.waitingCapacity)"
              :stroke-width="8"
              color="#3B82F6"
              :format="() => `${s.waitingCount}/${s.waitingCapacity}`"
            />
          </div>
          <div class="zone-item">
            <span class="zone-label">充电</span>
            <el-progress
              :percentage="capacityPct(s.chargingCount, s.chargingCapacity)"
              :stroke-width="8"
              color="#16A34A"
              :format="() => `${s.chargingCount}/${s.chargingCapacity}`"
            />
          </div>
        </div>

        <!-- 支持协议 -->
        <div class="protocol-tags">
          <el-tag
            v-for="p in s.supportedProtocols"
            :key="p.id"
            size="small"
            effect="plain"
            class="protocol-tag"
          >
            {{ p.name }}
          </el-tag>
        </div>
      </el-card>
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

function goToDetail(id: number) {
  router.push(`/stations/${id}`)
}

onMounted(() => {
  store.fetchStations()
})
</script>

<style scoped>
.station-list {
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1A1A1A;
  margin-bottom: 20px;
}

.station-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

@media (min-width: 768px) {
  .station-grid {
    grid-template-columns: 1fr 1fr;
  }
}

.station-card {
  border-radius: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.station-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.station-card.is-disabled {
  opacity: 0.7;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title-row h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1A1A1A;
}

.wait-time {
  font-size: 12px;
  color: #737373;
  white-space: nowrap;
}

.zone-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.zone-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zone-label {
  font-size: 12px;
  color: #737373;
  width: 32px;
  flex-shrink: 0;
}

.zone-item .el-progress {
  flex: 1;
}

.protocol-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.protocol-tag {
  font-size: 11px;
}

.loading-skeleton,
.empty-wrapper {
  padding: 48px 0;
}
</style>
