<template>
  <div class="report-view" v-loading="loading">
    <h2>数据报表</h2>

    <el-card shadow="never" class="report-card">
      <template #header>📊 充电量统计</template>
      <div class="summary-grid" v-if="volume">
        <div class="summary-item">
          <span class="summary-value">{{ volume.summary.totalEnergy }}</span>
          <span class="summary-label">总充电量 (kWh)</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">¥{{ volume.summary.totalRevenue }}</span>
          <span class="summary-label">总电费收入</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ volume.summary.totalSessions }}</span>
          <span class="summary-label">充电次数</span>
        </div>
      </div>
      <el-table v-if="volume?.byStation?.length" :data="volume.byStation" size="small" stripe class="report-table">
        <el-table-column prop="stationName" label="充电桩" />
        <el-table-column prop="totalEnergy" label="充电量 (kWh)" />
        <el-table-column prop="totalRevenue" label="电费收入" />
        <el-table-column prop="count" label="次数" />
      </el-table>
      <div v-else class="no-data">暂无充电量数据</div>
    </el-card>

    <el-card shadow="never" class="report-card">
      <template #header>💰 收入统计</template>
      <div class="summary-grid" v-if="revenue">
        <div class="summary-item">
          <span class="summary-value">¥{{ revenue.totalRevenue }}</span>
          <span class="summary-label">总收入</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">¥{{ revenue.electricityRevenue }}</span>
          <span class="summary-label">电费收入</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">¥{{ revenue.serviceRevenue }}</span>
          <span class="summary-label">服务费收入</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ revenue.paidSessions }}</span>
          <span class="summary-label">已支付订单</span>
        </div>
      </div>
      <div v-else class="no-data">暂无收入数据</div>
    </el-card>

    <el-card shadow="never" class="report-card">
      <template #header>🔌 充电桩利用率</template>
      <el-table v-if="utilization?.stations?.length" :data="utilization.stations" size="small" stripe class="report-table">
        <el-table-column prop="stationName" label="充电桩" />
        <el-table-column label="排队区利用率">
          <template #default="{ row }">
            <div class="util-bar">
              <el-progress :percentage="row.queueUtilization" :stroke-width="12" />
              <span class="util-text">{{ row.queueCount }}/{{ row.queueCapacity }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="等待区利用率">
          <template #default="{ row }">
            <div class="util-bar">
              <el-progress :percentage="row.waitingUtilization" :stroke-width="12" :color="row.waitingUtilization > 80 ? '#D97706' : '#3B82F6'" />
              <span class="util-text">{{ row.waitingCount }}/{{ row.waitingCapacity }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="充电区利用率">
          <template #default="{ row }">
            <div class="util-bar">
              <el-progress :percentage="row.chargingUtilization" :stroke-width="12" :color="row.chargingUtilization > 80 ? '#16A34A' : '#3B82F6'" />
              <span class="util-text">{{ row.chargingCount }}/{{ row.chargingCapacity }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="no-data">暂无利用率数据</div>
    </el-card>

    <div class="refresh-bar">
      <el-button type="primary" :icon="Refresh" @click="fetchReports" :loading="loading">刷新数据</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getChargingVolumeApi, getRevenueApi, getUtilizationApi } from '@/api/admin/report'

const loading = ref(true)
const volume = ref<any>(null)
const revenue = ref<any>(null)
const utilization = ref<any>(null)

async function fetchReports() {
  loading.value = true
  try {
    const [v, r, u] = await Promise.all([
      getChargingVolumeApi(),
      getRevenueApi(),
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
.report-view { max-width: 960px; }
.report-view h2 { font-size: 22px; font-weight: 600; color: #1E293B; margin-bottom: 20px; }
.report-card { border-radius: 10px; margin-bottom: 16px; }
.report-card :deep(.el-card__header) { font-weight: 600; font-size: 15px; }
.summary-grid { display: flex; gap: 24px; margin-bottom: 16px; flex-wrap: wrap; }
.summary-item { display: flex; flex-direction: column; align-items: center; min-width: 120px; padding: 12px 20px; background: #F8FAFC; border-radius: 8px; }
.summary-value { font-size: 24px; font-weight: 700; color: #1E293B; font-family: 'JetBrains Mono', monospace; }
.summary-label { font-size: 12px; color: #94A3B8; margin-top: 4px; }
.report-table { margin-top: 8px; }
.no-data { text-align: center; padding: 32px; color: #94A3B8; font-size: 14px; }
.util-bar { display: flex; align-items: center; gap: 8px; }
.util-bar .el-progress { flex: 1; }
.util-text { font-size: 12px; color: #64748B; font-family: 'JetBrains Mono', monospace; white-space: nowrap; }
.refresh-bar { margin-top: 8px; }
</style>
