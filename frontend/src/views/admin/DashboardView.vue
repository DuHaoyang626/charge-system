<template>
  <div class="admin-dashboard">
    <!-- ════════════ 顶部指标卡片 ════════════ -->
    <div class="metrics-responsive">
      <div class="glass-card metric-card" v-for="m in metrics" :key="m.label">
        <div class="metric-icon" :style="{ background: m.iconBg }">{{ m.icon }}</div>
        <div class="metric-info">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value" :style="{ color: m.color }">{{ m.value }}</div>
          <div class="metric-sub">{{ m.sub }}</div>
        </div>
      </div>
    </div>

    <!-- ════════════ 图表区域 ════════════ -->
    <div class="chart-grid">
      <div class="glass-card chart-card chart-span-2">
        <div class="chart-header">
          <span class="chart-title">📈 充电量趋势</span>
          <span class="glass-badge">近7日</span>
        </div>
        <div ref="trendChartRef" class="chart-container" style="height:280px;"></div>
        <div v-if="!trendData" class="chart-empty">暂无趋势数据</div>
      </div>

      <div class="glass-card chart-card">
        <div class="chart-header">
          <span class="chart-title">🔌 充电桩利用率</span>
          <span class="glass-badge">{{ runningCount }}/{{ totalCount }} 运行中</span>
        </div>
        <div ref="pieChartRef" class="chart-container" style="height:280px;"></div>
        <div v-if="!utilData" class="chart-empty">暂无利用率数据</div>
      </div>

      <div class="glass-card chart-card">
        <div class="chart-header">
          <span class="chart-title">💰 收入构成</span>
          <span class="glass-badge">本月</span>
        </div>
        <div ref="revenueChartRef" class="chart-container" style="height:240px;"></div>
        <div v-if="!revenueData" class="chart-empty">暂无收入数据</div>
      </div>

      <div class="glass-card chart-card">
        <div class="chart-header">
          <span class="chart-title">⚡ 充电桩状态分布</span>
        </div>
        <div ref="statusChartRef" class="chart-container" style="height:240px;"></div>
        <div v-if="!rawStations.length" class="chart-empty">暂无状态数据</div>
      </div>
    </div>

    <!-- ════════════ 充电站运营总览 ════════════ -->
    <div class="glass-card section-card">
      <div class="section-title">
        <span>🏗️ 充电桩运营详情</span>
        <button class="btn-glass btn-glass-sm" @click="refreshData" :disabled="loading">
          {{ loading ? '⟳ 刷新中...' : '⟳ 刷新' }}
        </button>
      </div>

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
                🚶{{ s.queueCount }}/{{ s.queueCapacity }}
                · ⏳{{ s.waitingCount }}/{{ s.waitingCapacity }}
                · ⚡{{ s.chargingCount }}/{{ s.chargingCapacity }}
              </span>
            </div>
            <el-tag type="info" size="small" effect="plain" v-if="s.estimatedWaitMinutes">
              预估等待 {{ s.estimatedWaitMinutes }} 分钟
            </el-tag>
          </div>

          <div class="zone-tables">
            <div class="zone-col glass-card-strong">
              <div class="zone-col-header" style="border-left-color: #3B82F6;">🚶 排队区</div>
              <table class="zone-table" v-if="s.queueList.length">
                <thead><tr><th>#</th><th>车牌</th><th>目标</th></tr></thead>
                <tbody>
                  <tr v-for="q in s.queueList" :key="q.sessionId">
                    <td>{{ q.position }}</td>
                    <td>{{ q.licensePlate }}</td>
                    <td>{{ q.requestedEnergyKwh }}kWh</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="zone-empty">空闲</div>
            </div>

            <div class="zone-col glass-card-strong">
              <div class="zone-col-header" style="border-left-color: #F59E0B;">⏳ 等待区</div>
              <table class="zone-table" v-if="s.waitingList.length">
                <thead><tr><th>#</th><th>车牌</th><th>目标</th></tr></thead>
                <tbody>
                  <tr v-for="q in s.waitingList" :key="q.sessionId">
                    <td>{{ q.position }}</td>
                    <td>{{ q.licensePlate }}</td>
                    <td>{{ q.requestedEnergyKwh }}kWh</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="zone-empty">空闲</div>
            </div>

            <div class="zone-col glass-card-strong">
              <div class="zone-col-header" style="border-left-color: #22C55E;">⚡ 充电区</div>
              <table class="zone-table" v-if="s.chargingList.length">
                <thead><tr><th>#</th><th>车牌</th><th>已充/目标</th><th>进度</th></tr></thead>
                <tbody>
                  <tr v-for="q in s.chargingList" :key="q.sessionId">
                    <td>{{ q.position }}</td>
                    <td>{{ q.licensePlate }}</td>
                    <td>{{ q.chargedEnergyKwh }}/{{ q.targetEnergyKwh }}kWh</td>
                    <td>
                      <el-progress :percentage="q.progress" :stroke-width="8" :width="80" />
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="zone-empty">空闲</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════════ 统计概览 ════════════ -->
    <div class="stats-grid">
      <div class="glass-card section-card">
        <div class="section-title">⚡ 充电量统计</div>
        <div class="insight-grid" v-if="volume">
          <div class="insight-item glass-card-strong">
            <span class="insight-val">{{ volume?.totalEnergyKwh ?? '--' }} kWh</span>
            <span class="insight-label">总充电量（已支付）</span>
          </div>
          <div class="insight-item glass-card-strong">
            <span class="insight-val">{{ volume?.totalSessions ?? '--' }}</span>
            <span class="insight-label">充电次数</span>
          </div>
        </div>
        <template v-if="volume?.dataPoints?.length">
          <div class="table-scroll">
            <el-table :data="volume.dataPoints" size="small" stripe>
              <el-table-column prop="period" label="时段" />
              <el-table-column prop="energyKwh" label="充电量 (kWh)" />
              <el-table-column prop="sessions" label="次数" />
            </el-table>
          </div>
        </template>
        <div v-else class="insight-empty">暂无充电量数据</div>
      </div>
      <div class="glass-card section-card">
        <div class="section-title">💰 收入统计</div>
        <div class="insight-grid" v-if="revenue">
          <div class="insight-item glass-card-strong">
            <span class="insight-val">¥{{ revenue?.totalRevenue ?? '0.00' }}</span>
            <span class="insight-label">总收入</span>
          </div>
          <div class="insight-item glass-card-strong">
            <span class="insight-val">¥{{ revenue?.electricityRevenue ?? '0.00' }}</span>
            <span class="insight-label">电费收入</span>
          </div>
          <div class="insight-item glass-card-strong">
            <span class="insight-val">¥{{ revenue?.serviceRevenue ?? '0.00' }}</span>
            <span class="insight-label">服务费收入</span>
          </div>
          <div class="insight-item glass-card-strong">
            <span class="insight-val">{{ revenue?.paidSessions ?? 0 }}</span>
            <span class="insight-label">已支付订单</span>
          </div>
        </div>
        <div v-else class="insight-empty">暂无收入数据</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getStationsApi, getStationDetailApi } from '@/api/station'
import { getChargingVolumeApi, getRevenueApi } from '@/api/admin/report'
import { POLLING_INTERVAL } from '@/utils/constants'

const loading = ref(false)
const rawStations = ref<any[]>([])
const stationDetails = ref<any[]>([])
const volume = ref<any>(null)
const revenue = ref<any>(null)

let pollingTimer: ReturnType<typeof setInterval> | null = null

// ECharts 实例
const trendChartRef = ref<HTMLElement | null>(null)
const pieChartRef = ref<HTMLElement | null>(null)
const revenueChartRef = ref<HTMLElement | null>(null)
const statusChartRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null
let revenueChart: echarts.ECharts | null = null
let statusChart: echarts.ECharts | null = null

const totalCount = computed(() => rawStations.value.length)
const runningCount = computed(() => rawStations.value.filter((s: any) => s.status === 'running').length)

// 充电趋势: dataPoints[{period, energyKwh, sessions}]
const trendData = computed(() => {
  if (!volume.value?.dataPoints?.length) return null
  return volume.value.dataPoints
})

const utilData = computed(() => {
  if (!rawStations.value.length) return null
  return rawStations.value
})

const revenueData = computed(() => revenue.value)

function startPolling() {
  stopPolling()
  pollingTimer = setInterval(() => fetchData(true), POLLING_INTERVAL)
}

function refreshData() { fetchData(false) }

function stopPolling() {
  if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null }
}

const metrics = computed(() => {
  const total = rawStations.value.length
  const running = rawStations.value.filter((s: any) => s.status === 'running').length
  const charging = rawStations.value.reduce((sum: number, s: any) => sum + (s.chargingCount || 0), 0)
  const queueing = rawStations.value.reduce((sum: number, s: any) => sum + (s.queueCount || 0), 0)
  return [
    { label: '充电桩总数', value: String(total), sub: `运行中 ${running} / 停止 ${total - running}`, color: 'var(--text-primary)', icon: '🔌', iconBg: 'rgba(37,99,235,0.10)' },
    { label: '正在充电', value: String(charging), sub: '所有桩合计', color: 'var(--color-success)', icon: '⚡', iconBg: 'rgba(22,163,74,0.10)' },
    { label: '排队等待', value: String(queueing), sub: `${rawStations.value.filter(s => s.queueCount > 0).length} 个桩有排队`, color: 'var(--color-warning)', icon: '⏳', iconBg: 'rgba(217,119,6,0.10)' },
    { label: '收入(已支付)', value: revenue.value?.totalRevenue != null ? `¥${revenue.value.totalRevenue}` : '--', sub: `电费 ¥${revenue.value?.electricityRevenue || 0}`, color: 'var(--color-primary)', icon: '💰', iconBg: 'rgba(37,99,235,0.10)' },
  ]
})

const stationData = computed(() => {
  if (stationDetails.value.length > 0) return stationDetails.value
  return rawStations.value.map((s: any) => ({
    ...s, queueList: [], waitingList: [], chargingList: [],
  }))
})

// ── 渲染 ECharts ──
function renderCharts() {
  renderTrendChart()
  renderPieChart()
  renderRevenueChart()
  renderStatusChart()
}

function renderTrendChart() {
  if (!trendChartRef.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }

  const points = trendData.value
  if (!points || !points.length) return

  const labels = points.map((p: any) => p.period)
  const energyData = points.map((p: any) => p.energyKwh ?? 0)

  trendChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.9)', borderColor: 'rgba(148,163,184,0.2)' },
    grid: { left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: 'var(--border-color)' } },
      axisLabel: { color: 'var(--text-tertiary)', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: 'kWh',
      nameTextStyle: { color: 'var(--text-tertiary)', fontSize: 11 },
      splitLine: { lineStyle: { color: 'var(--border-light)', type: 'dashed' } },
      axisLabel: { color: 'var(--text-tertiary)', fontSize: 11 },
    },
    series: [{
      type: 'line',
      data: energyData,
      smooth: true,
      lineStyle: { width: 3, color: '#3B82F6' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59,130,246,0.3)' },
          { offset: 1, color: 'rgba(59,130,246,0.02)' },
        ]),
      },
      itemStyle: { color: '#3B82F6' },
      symbol: 'circle',
      symbolSize: 6,
    }],
  })
}

function renderPieChart() {
  if (!pieChartRef.value) return
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }

  const stations = utilData.value
  if (!stations || !stations.length) return

  const pieData = stations.slice(0, 8).map((s: any) => {
    const total = (s.queueCapacity || 1) + (s.waitingCapacity || 1) + (s.chargingCapacity || 1)
    const used = (s.queueCount || 0) + (s.waitingCount || 0) + (s.chargingCount || 0)
    return {
      name: s.name || `桩${s.id}`,
      value: Math.round((used / total) * 100),
    }
  })

  const colors = ['#3B82F6', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']

  pieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}%',
      backgroundColor: 'rgba(255,255,255,0.9)',
      borderColor: 'rgba(148,163,184,0.2)',
    },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: 'transparent', borderWidth: 2 },
      label: {
        show: true,
        formatter: '{b}\n{d}%',
        fontSize: 10,
        color: 'var(--text-secondary)',
      },
      labelLine: { lineStyle: { color: 'var(--border-color)' } },
      data: pieData,
      color: colors,
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' },
      },
    }],
  })
}

function renderRevenueChart() {
  if (!revenueChartRef.value) return
  if (!revenueChart) {
    revenueChart = echarts.init(revenueChartRef.value)
  }

  const rev = revenueData.value
  if (!rev) return

  const barData = [
    { name: '电费', value: rev.electricityRevenue ?? 0 },
    { name: '服务费', value: rev.serviceRevenue ?? 0 },
  ]

  revenueChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.9)', borderColor: 'rgba(148,163,184,0.2)' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: barData.map(d => d.name),
      axisLine: { lineStyle: { color: 'var(--border-color)' } },
      axisLabel: { color: 'var(--text-tertiary)', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      name: '金额 (¥)',
      nameTextStyle: { color: 'var(--text-tertiary)', fontSize: 11 },
      splitLine: { lineStyle: { color: 'var(--border-light)', type: 'dashed' } },
      axisLabel: { color: 'var(--text-tertiary)', fontSize: 11, formatter: '¥{value}' },
    },
    series: [{
      type: 'bar',
      data: barData.map(d => d.value),
      barWidth: '50%',
      itemStyle: {
        borderRadius: [6, 6, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#3B82F6' },
          { offset: 1, color: '#1D4ED8' },
        ]),
      },
      emphasis: { itemStyle: { color: '#2563EB' } },
    }],
  })
}

function renderStatusChart() {
  if (!statusChartRef.value) return
  if (!statusChart) {
    statusChart = echarts.init(statusChartRef.value)
  }

  const stations = rawStations.value
  if (!stations || !stations.length) return

  const running = stations.filter((s: any) => s.status === 'running').length
  const stopped = stations.filter((s: any) => s.status === 'stopped' || s.status === 'stopping').length
  const error = stations.filter((s: any) => s.status === 'error').length
  const statusData = [
    running > 0 ? { name: '运行中', value: running, itemStyle: { color: '#22C55E' } } : null,
    stopped > 0 ? { name: '已停止', value: stopped, itemStyle: { color: '#94A3B8' } } : null,
    error > 0 ? { name: '异常', value: error, itemStyle: { color: '#EF4444' } } : null,
  ].filter(Boolean)

  if (!statusData.length) return

  statusChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: 'rgba(255,255,255,0.9)',
      borderColor: 'rgba(148,163,184,0.2)',
    },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 4, borderColor: 'transparent', borderWidth: 2 },
      label: {
        show: true,
        formatter: '{b}\n{c}',
        fontSize: 12,
        color: 'var(--text-secondary)',
      },
      labelLine: { lineStyle: { color: 'var(--border-color)' } },
      data: statusData,
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' },
      },
    }],
  })
}

async function fetchData(silent = false) {
  if (!silent) loading.value = true
  try {
    // 默认查询最近30天
    const end = new Date()
    const start = new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000)
    const fmt = (d: Date) => d.toISOString().slice(0, 10)
    const dateParams = { startDate: fmt(start), endDate: fmt(end), granularity: 'day' }

    const [staRes, volRes, revRes] = await Promise.all([
      getStationsApi(),
      getChargingVolumeApi(dateParams),
      getRevenueApi(dateParams),
    ])
    const body = staRes.data as any
    rawStations.value = body.data?.stations || []

    const promises = rawStations.value.map(async (s: any) => {
      try {
        const detailRes = await getStationDetailApi(s.id)
        return (detailRes.data as any).data || s
      } catch { return { ...s, queueList: [], waitingList: [], chargingList: [] } }
    })
    stationDetails.value = await Promise.all(promises)

    // volume 结构: { totalEnergyKwh, totalSessions, dataPoints: [{period, energyKwh, sessions}] }
    volume.value = (volRes.data as any).data

    // revenue 结构: { totalRevenue, electricityRevenue, serviceRevenue, dataPoints: [...] }
    revenue.value = (revRes.data as any).data

    nextTick(() => renderCharts())
  } catch {
    if (!silent) ElMessage.error('获取数据失败，请检查后端是否运行')
    rawStations.value = []
    stationDetails.value = []
  } finally { loading.value = false }
}

function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
  revenueChart?.resize()
  statusChart?.resize()
}

onMounted(() => { fetchData(); startPolling(); window.addEventListener('resize', handleResize) })
onUnmounted(() => {
  stopPolling()
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
  revenueChart?.dispose()
  statusChart?.dispose()
})
</script>

<style scoped>
.admin-dashboard { display: flex; flex-direction: column; gap: clamp(16px, 2vw, 20px); }

/* 指标卡片 / 图表网格 / 统计网格 */
.metrics-responsive { display: grid; gap: clamp(10px, 1vw, 16px); grid-template-columns: repeat(auto-fit, minmax(min(100%, 180px), 1fr)); }
.chart-grid { display: grid; gap: clamp(12px, 1.5vw, 16px); grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr)); }
.chart-span-2 { grid-column: span 2; }
.stats-grid { display: grid; gap: clamp(12px, 1.5vw, 16px); grid-template-columns: repeat(auto-fit, minmax(min(100%, 400px), 1fr)); }

@media (max-width: 600px) {
  .chart-span-2 { grid-column: span 1; }
}

.metric-card {
  display: flex;
  align-items: center;
  gap: clamp(12px, 1.5vw, 16px);
  padding: clamp(14px, 2vw, 20px);
  transition: all 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), var(--shadow-glass);
}

.metric-icon {
  width: clamp(40px, 5vw, 48px);
  height: clamp(40px, 5vw, 48px);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: clamp(20px, 2.5vw, 24px);
  flex-shrink: 0;
}

.metric-info { flex: 1; min-width: 0; }
.metric-label { font-size: clamp(12px, 1.1vw, 13px); color: var(--text-tertiary); margin-bottom: 2px; }
.metric-value { font-size: clamp(22px, 3vw, 28px); font-weight: 700; font-family: 'JetBrains Mono', monospace; line-height: 1.2; }
.metric-sub { font-size: clamp(11px, 1vw, 12px); color: var(--text-tertiary); margin-top: 2px; }

/* 图表卡片 */
.chart-card {
  padding: clamp(14px, 2vw, 20px);
  margin-bottom: 0;
  position: relative;
}
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.chart-title { font-size: clamp(14px, 1.3vw, 15px); font-weight: 600; color: var(--text-primary); }
.chart-container { width: 100%; }
.chart-empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--text-tertiary); font-size: 14px; pointer-events: none; }

/* 运营详情 */
.section-card { padding: clamp(16px, 2.5vw, 24px); }
.section-title { font-size: clamp(15px, 1.5vw, 16px); font-weight: 600; color: var(--text-primary); display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 8px; flex-wrap: wrap; }

.station-block { padding: clamp(12px, 1.5vw, 16px) 0; border-bottom: 1px solid var(--border-light); }
.station-block:last-child { border-bottom: none; }
.station-block-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.station-block-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.station-name { font-size: clamp(14px, 1.5vw, 16px); font-weight: 600; color: var(--text-primary); }
.station-metrics { font-size: clamp(11px, 1vw, 12px); color: var(--text-tertiary); font-family: 'JetBrains Mono', monospace; }

.zone-tables { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); gap: clamp(8px, 1vw, 12px); }
.zone-col { border-radius: 8px; overflow: hidden; }
.zone-col-header { font-size: clamp(12px, 1.1vw, 13px); font-weight: 600; padding: 8px 12px; border-left: 3px solid; border-bottom: 1px solid var(--border-light); color: var(--text-primary); }
.zone-table { width: 100%; border-collapse: collapse; font-size: clamp(11px, 1vw, 12px); }
.zone-table thead th { padding: 6px 8px; text-align: left; color: var(--text-tertiary); font-weight: 500; border-bottom: 1px solid var(--border-light); }
.zone-table tbody td { padding: 6px 8px; border-bottom: 1px solid var(--border-light); color: var(--text-secondary); }
.zone-table tbody tr:last-child td { border-bottom: none; }
.zone-empty { padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 13px; }

/* 统计概览 */
.insight-grid { display: flex; gap: clamp(8px, 1vw, 12px); flex-wrap: wrap; margin-bottom: 16px; }
.insight-item { display: flex; flex-direction: column; align-items: center; min-width: 80px; padding: clamp(10px, 1.2vw, 16px); border-radius: 8px; flex: 1; }
.insight-val { font-size: clamp(17px, 2vw, 20px); font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
.insight-label { font-size: clamp(11px, 1vw, 12px); color: var(--text-tertiary); margin-top: 4px; }
.insight-empty { text-align: center; padding: 32px; color: var(--text-tertiary); font-size: 14px; }
</style>
