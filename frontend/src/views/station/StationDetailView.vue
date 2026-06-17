<template>
  <div class="station-detail" v-if="detail">
    <div class="detail-header">
      <button class="btn-glass btn-glass-sm" @click="goBack">← 返回</button>
      <h2>{{ detail.name }}</h2>
      <StationStatusBadge :status="detail.status" />
    </div>

    <div class="capacity-row responsive-grid-3">
      <div class="glass-card capacity-card">
        <p class="cap-label">🚶 排队区</p>
        <p class="cap-value">{{ detail.queueCount }}<span class="cap-total"> / {{ detail.queueCapacity }}</span></p>
      </div>
      <div class="glass-card capacity-card">
        <p class="cap-label">⏳ 等待区</p>
        <p class="cap-value">{{ detail.waitingCount }}<span class="cap-total"> / {{ detail.waitingCapacity }}</span></p>
      </div>
      <div class="glass-card capacity-card">
        <p class="cap-label">⚡ 充电区</p>
        <p class="cap-value">{{ detail.chargingCount }}<span class="cap-total"> / {{ detail.chargingCapacity }}</span></p>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="zone-tabs">
      <el-tab-pane label="🚶 排队区" name="queue">
        <div v-if="detail.queueList.length > 0" class="glass-card table-scroll">
          <el-table :data="detail.queueList" stripe>
            <el-table-column prop="position" label="位置" width="70" />
            <el-table-column prop="licensePlate" label="车牌号" min-width="100" />
            <el-table-column prop="requestedEnergyKwh" label="目标电量" width="110">
              <template #default="{ row }">{{ row.requestedEnergyKwh }} kWh</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }"><ChargingStatusBadge :status="row.status" /></template>
            </el-table-column>
          </el-table>
        </div>
        <EmptyState v-else description="排队区暂无车辆" />
      </el-tab-pane>
      <el-tab-pane label="⏳ 等待区" name="waiting">
        <div v-if="detail.waitingList.length > 0" class="glass-card table-scroll">
          <el-table :data="detail.waitingList" stripe>
            <el-table-column prop="position" label="位置" width="70" />
            <el-table-column prop="licensePlate" label="车牌号" min-width="100" />
            <el-table-column prop="requestedEnergyKwh" label="目标电量" width="110">
              <template #default="{ row }">{{ row.requestedEnergyKwh }} kWh</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }"><ChargingStatusBadge :status="row.status" /></template>
            </el-table-column>
          </el-table>
        </div>
        <EmptyState v-else description="等待区暂无车辆" />
      </el-tab-pane>
      <el-tab-pane label="⚡ 充电区" name="charging">
        <div v-if="detail.chargingList.length > 0" class="glass-card table-scroll">
          <el-table :data="detail.chargingList" stripe>
            <el-table-column prop="position" label="位号" width="70" />
            <el-table-column prop="licensePlate" label="车牌号" min-width="100" />
            <el-table-column prop="chargedEnergyKwh" label="已充电量" width="110">
              <template #default="{ row }">{{ row.chargedEnergyKwh }} kWh</template>
            </el-table-column>
            <el-table-column label="进度" min-width="140">
              <template #default="{ row }"><el-progress :percentage="row.progress" :stroke-width="8" /></template>
            </el-table-column>
            <el-table-column label="协议" width="110">
              <template #default="{ row }">{{ row.protocol?.name || '--' }}</template>
            </el-table-column>
          </el-table>
        </div>
        <EmptyState v-else description="充电区暂无车辆" />
      </el-tab-pane>
    </el-tabs>

    <div class="glass-card protocol-card">
      <div class="protocol-header">🔌 支持协议</div>
      <div class="protocol-list">
        <el-tag v-for="p in detail.supportedProtocols" :key="p.id" class="glass-badge">{{ p.name }}（{{ p.powerKw }}kW）</el-tag>
      </div>
    </div>
  </div>
  <div v-else-if="loading" class="loading-wrapper"><el-skeleton :rows="5" animated /></div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStationStore } from '@/stores/station'
import StationStatusBadge from '@/components/StationStatusBadge.vue'
import ChargingStatusBadge from '@/components/ChargingStatusBadge.vue'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const router = useRouter()
const store = useStationStore()
const activeTab = ref('queue')
const loading = computed(() => store.loading)
const detail = computed(() => store.currentDetail)

function goBack() { router.push('/') }
onMounted(async () => {
  const id = Number(route.params.id)
  if (!isNaN(id)) await store.fetchDetail(id)
})
</script>

<style scoped>
.station-detail { max-width: 960px; margin: 0 auto; }
.detail-header { display: flex; align-items: center; gap: clamp(8px, 1.2vw, 12px); margin-bottom: clamp(16px, 2vw, 20px); flex-wrap: wrap; }
.detail-header h2 { font-size: clamp(17px, 2vw, 20px); font-weight: 600; color: var(--text-primary); }
.capacity-card { text-align: center; padding: clamp(14px, 2vw, 20px); }
.cap-label { font-size: clamp(12px, 1.2vw, 13px); color: var(--text-tertiary); margin-bottom: 6px; }
.cap-value { font-size: clamp(22px, 3vw, 28px); font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
.cap-total { font-size: clamp(12px, 1.2vw, 14px); color: var(--text-tertiary); font-weight: 400; }
.zone-tabs { margin-bottom: 20px; }
.zone-tabs :deep(.el-tabs__item) { font-size: clamp(13px, 1.2vw, 14px); }
.protocol-card { padding: clamp(16px, 2vw, 20px); }
.protocol-header { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; }
.protocol-list { display: flex; flex-wrap: wrap; gap: 8px; }
.loading-wrapper { padding: 48px; }
</style>
