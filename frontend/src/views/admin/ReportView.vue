<template>
  <div class="report-view">
    <div class="page-header">
      <div>
        <h2>📊 数据报表</h2>
        <p class="page-desc">充电量、收入和利用率统计</p>
      </div>
      <button class="btn-glass btn-glass-primary" @click="fetchReports" :disabled="loading">
        {{ loading ? '⟳ 刷新中...' : '⟳ 刷新数据' }}
      </button>
    </div>

    <div class="glass-card report-card">
      <div class="card-title">⚡ 充电量统计</div>
      <div class="summary-grid" v-if="volume">
        <div class="insight-item glass-card-strong">
          <span class="summary-value">{{ volume?.totalEnergyKwh ?? '--' }}</span>
          <span class="summary-label">总充电量 (kWh)</span>
        </div>
        <div class="insight-item glass-card-strong">
          <span class="summary-value">{{ volume?.totalSessions ?? '--' }}</span>
          <span class="summary-label">充电次数</span>
        </div>
      </div>
      <el-table v-if="volume?.dataPoints?.length" :data="volume.dataPoints" size="small" stripe class="report-table">
        <el-table-column prop="period" label="时段" />
        <el-table-column prop="energyKwh" label="充电量 (kWh)" />
        <el-table-column prop="sessions" label="次数" />
      </el-table>
      <div v-else class="no-data">暂无充电量数据</div>
    </div>

    <div class="glass-card report-card">
      <div class="card-title">💰 收入统计</div>
      <div class="summary-grid" v-if="revenue">
        <div class="insight-item glass-card-strong">
          <span class="summary-value">¥{{ revenue.totalRevenue }}</span>
          <span class="summary-label">总收入</span>
        </div>
        <div class="insight-item glass-card-strong">
          <span class="summary-value">¥{{ revenue.electricityRevenue }}</span>
          <span class="summary-label">电费收入</span>
        </div>
        <div class="insight-item glass-card-strong">
          <span class="summary-value">¥{{ revenue.serviceRevenue }}</span>
          <span class="summary-label">服务费收入</span>
        </div>
        <div class="insight-item glass-card-strong">
          <span class="summary-value">{{ revenue.paidSessions }}</span>
          <span class="summary-label">已支付订单</span>
        </div>
      </div>
      <div v-else class="no-data">暂无收入数据</div>
    </div>

    <div class="glass-card report-card">
      <div class="card-title">🔌 充电桩利用率</div>
      <el-table v-if="utilization?.stations?.length" :data="utilization.stations" size="small" stripe class="report-table">
        <el-table-column prop="stationName" label="充电桩" />
        <el-table-column label="排队区利用率">
          <template #default="{ row }">
            <div class="util-bar">
              <el-progress :percentage="row.queueUtilization" :stroke-width="10" />
              <span class="util-text">{{ row.queueCount }}/{{ row.queueCapacity }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="等待区利用率">
          <template #default="{ row }">
            <div class="util-bar">
              <el-progress :percentage="row.waitingUtilization" :stroke-width="10" :color="row.waitingUtilization > 80 ? '#D97706' : '#3B82F6'" />
              <span class="util-text">{{ row.waitingCount }}/{{ row.waitingCapacity }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="充电区利用率">
          <template #default="{ row }">
            <div class="util-bar">
              <el-progress :percentage="row.chargingUtilization" :stroke-width="10" :color="row.chargingUtilization > 80 ? '#22C55E' : '#3B82F6'" />
              <span class="util-text">{{ row.chargingCount }}/{{ row.chargingCapacity }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="no-data">暂无利用率数据</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getChargingVolumeApi, getRevenueApi, getUtilizationApi } from '@/api/admin/report'

const loading = ref(true)
const volume = ref<any>(null)
const revenue = ref<any>(null)
const utilization = ref<any>(null)

async function fetchReports() {
  loading.value = true
  try {
    const end = new Date()
    const start = new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000)
    const fmt = (d: Date) => d.toISOString().slice(0, 10)
    const dateParams = { startDate: fmt(start), endDate: fmt(end), granularity: 'day' }

    const [v, r, u] = await Promise.all([
      getChargingVolumeApi(dateParams),
      getRevenueApi(dateParams),
      getUtilizationApi(),
    ])
    volume.value = (v.data as any).data
    revenue.value = (r.data as any).data
    utilization.value = (u.data as any).data
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '加载报表失败')
  } finally { loading.value = false }
}

onMounted(fetchReports)
</script>

<style scoped>
.report-view { max-width: 960px; display: flex; flex-direction: column; gap: 16px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-header h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.report-card {
  padding: 24px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.summary-grid {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.insight-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 120px;
  padding: 16px 24px;
  border-radius: 8px;
  flex: 1;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
}

.summary-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.report-table {
  margin-top: 8px;
}

.no-data {
  text-align: center;
  padding: 32px;
  color: var(--text-tertiary);
  font-size: 14px;
}

.util-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.util-bar .el-progress {
  flex: 1;
}

.util-text {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
}
</style>
