<template>
  <div class="station-detail" v-if="detail">
    <!-- 顶部：返回 + 标题 -->
    <div class="detail-header">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h2>{{ detail.name }}</h2>
      <StationStatusBadge :status="detail.status" />
    </div>

    <!-- 容量概览 -->
    <el-row :gutter="16" class="capacity-row">
      <el-col :span="8">
        <el-card shadow="never" class="capacity-card">
          <p class="cap-label">排队区</p>
          <p class="cap-value">{{ detail.queueCount }}<span class="cap-total"> / {{ detail.queueCapacity }}</span></p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="capacity-card">
          <p class="cap-label">等待区</p>
          <p class="cap-value">{{ detail.waitingCount }}<span class="cap-total"> / {{ detail.waitingCapacity }}</span></p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="capacity-card">
          <p class="cap-label">充电区</p>
          <p class="cap-value">{{ detail.chargingCount }}<span class="cap-total"> / {{ detail.chargingCapacity }}</span></p>
        </el-card>
      </el-col>
    </el-row>

    <!-- 三区列表 -->
    <el-tabs v-model="activeTab" class="zone-tabs">
      <el-tab-pane label="排队区" name="queue">
        <el-table :data="detail.queueList" stripe v-if="detail.queueList.length > 0">
          <el-table-column prop="position" label="位置" width="80" />
          <el-table-column prop="licensePlate" label="车牌号" />
          <el-table-column prop="requestedEnergyKwh" label="目标电量" width="120">
            <template #default="{ row }">{{ row.requestedEnergyKwh }} kWh</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <ChargingStatusBadge :status="row.status" />
            </template>
          </el-table-column>
        </el-table>
        <EmptyState v-else description="排队区暂无车辆" />
      </el-tab-pane>

      <el-tab-pane label="等待区" name="waiting">
        <el-table :data="detail.waitingList" stripe v-if="detail.waitingList.length > 0">
          <el-table-column prop="position" label="位置" width="80" />
          <el-table-column prop="licensePlate" label="车牌号" />
          <el-table-column prop="requestedEnergyKwh" label="目标电量" width="120">
            <template #default="{ row }">{{ row.requestedEnergyKwh }} kWh</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <ChargingStatusBadge :status="row.status" />
            </template>
          </el-table-column>
        </el-table>
        <EmptyState v-else description="等待区暂无车辆" />
      </el-tab-pane>

      <el-tab-pane label="充电区" name="charging">
        <el-table :data="detail.chargingList" stripe v-if="detail.chargingList.length > 0">
          <el-table-column prop="position" label="位号" width="80" />
          <el-table-column prop="licensePlate" label="车牌号" />
          <el-table-column prop="chargedEnergyKwh" label="已充电量" width="120">
            <template #default="{ row }">{{ row.chargedEnergyKwh }} kWh</template>
          </el-table-column>
          <el-table-column prop="progress" label="进度" width="160">
            <template #default="{ row }">
              <el-progress :percentage="row.progress" :stroke-width="12" />
            </template>
          </el-table-column>
          <el-table-column label="协议" width="130">
            <template #default="{ row }">{{ row.protocol?.name || '--' }}</template>
          </el-table-column>
        </el-table>
        <EmptyState v-else description="充电区暂无车辆" />
      </el-tab-pane>
    </el-tabs>

    <!-- 支持协议 -->
    <el-card shadow="never" class="protocol-card">
      <template #header>支持协议</template>
      <div class="protocol-list">
        <el-tag v-for="p in detail.supportedProtocols" :key="p.id" class="protocol-tag" effect="plain">
          {{ p.name }}（{{ p.powerKw }}kW）
        </el-tag>
      </div>
    </el-card>
  </div>

  <div v-else-if="loading" class="loading-wrapper">
    <el-skeleton :rows="5" animated />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
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

function goBack() {
  router.push('/')
}

onMounted(async () => {
  const id = Number(route.params.id)
  if (!isNaN(id)) {
    await store.fetchDetail(id)
  }
})
</script>

<style scoped>
.station-detail {
  max-width: 900px;
  margin: 0 auto;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.detail-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1A1A1A;
}

.capacity-row {
  margin-bottom: 20px;
}

.capacity-card {
  text-align: center;
  border-radius: 12px;
}

.cap-label {
  font-size: 13px;
  color: #737373;
  margin-bottom: 4px;
}

.cap-value {
  font-size: 28px;
  font-weight: 700;
  color: #1A1A1A;
  font-family: 'JetBrains Mono', monospace;
}

.cap-total {
  font-size: 14px;
  color: #9CA3AF;
  font-weight: 400;
}

.zone-tabs {
  margin-bottom: 20px;
}

.protocol-card {
  border-radius: 12px;
}

.protocol-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.protocol-tag {
  font-size: 13px;
}

.loading-wrapper {
  padding: 48px;
}
</style>
