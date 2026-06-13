<template>
  <div class="admin-dashboard">
    <!-- ════════════ 顶部指标卡片 ════════════ -->
    <el-row :gutter="16" class="metrics-row">
      <el-col :xs="12" :sm="6" v-for="m in metrics" :key="m.label">
        <el-card shadow="never" class="metric-card">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value" :style="{ color: m.color }">{{ m.value }}</div>
          <div class="metric-sub">{{ m.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ════════════ 充电站运营总览 ════════════ -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="section-title">
          <span>充电桩运营状态</span>
          <el-button size="small" text @click="refreshData" :loading="loading" :icon="Refresh">刷新</el-button>
        </div>
      </template>

      <div v-loading="loading">
        <div v-for="s in stationData" :key="s.id" class="station-block">
          <div class="station-block-header">
            <div class="station-block-title">
              <span class="station-name">{{ s.name }}</span>
              <el-tag :type="s.status === 'running' ? 'success' : s.status === 'stopping' ? 'warning' : 'info'"
                      size="small" effect="plain">
                {{ s.status === 'running' ? '运行中' : s.status === 'stopping' ? '停止中' : '已停止' }}
              </el-tag>
              <span class="station-metrics">
                🚗排队{{ s.queueCount }}/{{ s.queueCapacity }}
                · ⏳等待{{ s.waitingCount }}/{{ s.waitingCapacity }}
                · ⚡充电{{ s.chargingCount }}/{{ s.chargingCapacity }}
              </span>
            </div>
            <el-tag type="info" size="small" effect="plain" v-if="s.estimatedWaitMinutes">
              预估等待 {{ s.estimatedWaitMinutes }} 分钟
            </el-tag>
          </div>

          <!-- 三区表格 -->
          <div class="zone-tables">
            <div class="zone-col">
              <div class="zone-col-header" style="border-left-color: #2563EB;">🚶 排队区</div>
              <table class="zone-table" v-if="s.queueList.length">
                <thead><tr><th>#</th><th>车牌</th><th>目标</th><th>等待</th></tr></thead>
                <tbody>
                  <tr v-for="q in s.queueList" :key="q.sessionId">
                    <td>{{ q.position }}</td>
                    <td>{{ q.licensePlate }}</td>
                    <td>{{ q.requestedEnergyKwh }}kWh</td>
                    <td>{{ q.estimatedWaitMinutes }}min</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="zone-empty">空闲</div>
            </div>

            <div class="zone-col">
              <div class="zone-col-header" style="border-left-color: #3B82F6;">⏳ 等待区</div>
              <table class="zone-table" v-if="s.waitingList.length">
                <thead><tr><th>#</th><th>车牌</th><th>目标</th><th>等待</th></tr></thead>
                <tbody>
                  <tr v-for="q in s.waitingList" :key="q.sessionId">
                    <td>{{ q.position }}</td>
                    <td>{{ q.licensePlate }}</td>
                    <td>{{ q.requestedEnergyKwh }}kWh</td>
                    <td>{{ q.estimatedWaitMinutes }}min</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="zone-empty">空闲</div>
            </div>

            <div class="zone-col">
              <div class="zone-col-header" style="border-left-color: #16A34A;">⚡ 充电区</div>
              <table class="zone-table" v-if="s.chargingList.length">
                <thead><tr><th>#</th><th>车牌</th><th>已充/目标</th><th>进度</th></tr></thead>
                <tbody>
                  <tr v-for="q in s.chargingList" :key="q.sessionId">
                    <td>{{ q.position }}</td>
                    <td>{{ q.licensePlate }}</td>
                    <td>{{ q.chargedEnergyKwh }}/{{ q.targetEnergyKwh }}kWh</td>
                    <td>
                      <el-progress :percentage="q.progress" :stroke-width="10" :width="80" />
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="zone-empty">空闲</div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- ════════════ 今日充电汇总 ════════════ -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header><span class="section-title">⚡ 今日充电趋势</span></template>
          <div class="chart-placeholder">
            <div class="bar-chart">
              <div v-for="(b, i) in barData" :key="i" class="bar-item">
                <div class="bar-fill" :style="{ height: b.pct + '%' }"></div>
                <span class="bar-label">{{ b.label }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header><span class="section-title">💰 收入分布</span></template>
          <div class="revenue-breakdown">
            <div class="rev-row">
              <span class="rev-label">电费收入</span>
              <el-progress :percentage="65" color="#2563EB" :stroke-width="16" :format="() => '¥2,580.00'" />
            </div>
            <div class="rev-row">
              <span class="rev-label">服务费收入</span>
              <el-progress :percentage="35" color="#D97706" :stroke-width="16" :format="() => '¥1,380.00'" />
            </div>
            <div class="rev-total">
              今日总收入 <strong>¥3,960.00</strong>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getStationsApi, getStationDetailApi } from '@/api/station'
import { POLLING_INTERVAL } from '@/utils/constants'

const loading = ref(false)
const rawStations = ref<any[]>([])
const stationDetails = ref<any[]>([])

let pollingTimer: ReturnType<typeof setInterval> | null = null

function startPolling() {
  stopPolling()
  pollingTimer = setInterval(() => {
    fetchData(true)  // silent refresh
  }, POLLING_INTERVAL)
}

function refreshData() {
  fetchData(false)  // with loading indicator
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

// ── 实时指标（从 API 数据计算，演示环境缺少的值用默认值） ──
const metrics = computed(() => {
  const total = rawStations.value.length
  const running = rawStations.value.filter((s: any) => s.status === 'running').length
  const charging = rawStations.value.reduce((sum: number, s: any) => sum + (s.chargingCount || 0), 0)
  const queueing = rawStations.value.reduce((sum: number, s: any) => sum + (s.queueCount || 0), 0)
  return [
    { label: '充电桩总数', value: String(total), sub: `运行中 ${running} / 停止 ${total - running}`, color: '#1A1A1A' },
    { label: '正在充电', value: String(charging), sub: '所有充电桩合计', color: '#16A34A' },
    { label: '排队等待', value: String(queueing), sub: `${rawStations.value.filter(s => s.queueCount > 0).length} 个桩有排队`, color: '#D97706' },
    { label: '运行中', value: String(running), sub: `停止 ${total - running}`, color: '#2563EB' },
  ]
})

// ── 详细充电站数据（含三区列表） ──
const stationData = computed(() => {
  if (stationDetails.value.length > 0) return stationDetails.value
  return rawStations.value.map((s: any) => ({
    ...s,
    queueList: [],
    waitingList: [],
    chargingList: [],
  }))
})

// ── 柱状图和收入（模拟，后端暂无对应接口） ──
const barData = [
  { label: '08时', pct: 15 },
  { label: '10时', pct: 45 },
  { label: '12时', pct: 30 },
  { label: '14时', pct: 65 },
  { label: '16时', pct: 55 },
  { label: '18时', pct: 80 },
  { label: '20时', pct: 70 },
  { label: '22时', pct: 40 },
]

async function fetchData(silent = false) {
  if (!silent) loading.value = true
  try {
    const res = await getStationsApi()
    const body = res.data as any
    rawStations.value = body.data?.stations || body?.stations || []

    // 并行拉取每个桩的详情（获取三区车辆列表）
    const promises = rawStations.value.map(async (s: any) => {
      try {
        const detailRes = await getStationDetailApi(s.id)
        return (detailRes.data as any).data || s
      } catch {
        return { ...s, queueList: [], waitingList: [], chargingList: [] }
      }
    })
    stationDetails.value = await Promise.all(promises)
  } catch {
    ElMessage.error('获取数据失败，请检查后端是否运行')
    rawStations.value = []
    stationDetails.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.admin-dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── 指标卡片 ── */
.metrics-row {
  margin-bottom: 0 !important;
}

.metric-card {
  border-radius: 10px;
  text-align: center;
}

.metric-label {
  font-size: 13px;
  color: #64748B;
  margin-bottom: 6px;
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1.1;
}

.metric-sub {
  font-size: 12px;
  color: #94A3B8;
  margin-top: 4px;
}

/* ── 区块通用 ── */
.section-card {
  border-radius: 10px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* ── 充电站区块 ── */
.station-block {
  padding: 16px 0;
  border-bottom: 1px solid #F1F5F9;
}

.station-block:last-child { border-bottom: none; }

.station-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.station-block-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.station-name {
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
}

.station-metrics {
  font-size: 12px;
  color: #64748B;
  font-family: 'JetBrains Mono', monospace;
}

/* ── 三区表格 ── */
.zone-tables {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.zone-col {
  background: #F8FAFC;
  border-radius: 8px;
  overflow: hidden;
}

.zone-col-header {
  font-size: 13px;
  font-weight: 600;
  padding: 8px 12px;
  background: #FFFFFF;
  border-left: 3px solid;
  border-bottom: 1px solid #E2E8F0;
}

.zone-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.zone-table thead th {
  padding: 6px 8px;
  text-align: left;
  color: #94A3B8;
  font-weight: 500;
  border-bottom: 1px solid #E2E8F0;
}

.zone-table tbody td {
  padding: 6px 8px;
  border-bottom: 1px solid #F1F5F9;
  color: #334155;
}

.zone-table tbody tr:last-child td {
  border-bottom: none;
}

.zone-empty {
  padding: 24px;
  text-align: center;
  color: #94A3B8;
  font-size: 13px;
}

/* ── 柱状图 ── */
.chart-placeholder {
  padding: 8px 0;
}

.bar-chart {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 120px;
  gap: 8px;
}

.bar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.bar-fill {
  width: 100%;
  max-width: 32px;
  background: linear-gradient(to top, #2563EB, #60A5FA);
  border-radius: 4px 4px 0 0;
  min-height: 4px;
  transition: height 0.3s;
}

.bar-label {
  font-size: 11px;
  color: #94A3B8;
}

/* ── 收入 ── */
.revenue-breakdown {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rev-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rev-label {
  font-size: 13px;
  color: #475569;
}

.rev-total {
  text-align: right;
  font-size: 14px;
  color: #475569;
  padding-top: 8px;
  border-top: 1px solid #E2E8F0;
}

.rev-total strong {
  font-size: 20px;
  color: #EA580C;
  font-family: 'JetBrains Mono', monospace;
  margin-left: 8px;
}
</style>
