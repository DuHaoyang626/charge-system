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
                🚶排队{{ s.queueCount }}/{{ s.queueCapacity }}
                · ⏳等待{{ s.waitingCount }}/{{ s.waitingCapacity }}
                · ⚡充电{{ s.chargingCount }}/{{ s.chargingCapacity }}
              </span>
            </div>
            <el-tag type="info" size="small" effect="plain" v-if="s.estimatedWaitMinutes">
              预估等待 {{ s.estimatedWaitMinutes }} 分钟
            </el-tag>
          </div>

          <div class="zone-tables">
            <div class="zone-col">
              <div class="zone-col-header" style="border-left-color: #2563EB;">🚶 排队区</div>
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

            <div class="zone-col">
              <div class="zone-col-header" style="border-left-color: #3B82F6;">⏳ 等待区</div>
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

    <!-- ════════════ 统计概览 ════════════ -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header><span class="section-title">⚡ 充电量统计</span></template>
          <div class="insight-grid" v-if="volume">
            <div class="insight-item">
              <span class="insight-val">{{ volume.summary.totalEnergy }} kWh</span>
              <span class="insight-label">总充电量（已支付）</span>
            </div>
            <div class="insight-item">
              <span class="insight-val">{{ volume.summary.totalSessions }}</span>
              <span class="insight-label">充电次数</span>
            </div>
          </div>
          <el-table v-if="volume?.byStation?.length" :data="volume.byStation" size="small" stripe>
            <el-table-column prop="stationName" label="桩" />
            <el-table-column prop="totalEnergy" label="充电量 (kWh)" />
            <el-table-column prop="count" label="次数" />
          </el-table>
          <div v-else class="insight-empty">暂无充电量数据</div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header><span class="section-title">💰 收入统计</span></template>
          <div class="insight-grid" v-if="revenue">
            <div class="insight-item">
              <span class="insight-val">¥{{ revenue.totalRevenue }}</span>
              <span class="insight-label">总收入</span>
            </div>
            <div class="insight-item">
              <span class="insight-val">¥{{ revenue.electricityRevenue }}</span>
              <span class="insight-label">电费收入</span>
            </div>
            <div class="insight-item">
              <span class="insight-val">¥{{ revenue.serviceRevenue }}</span>
              <span class="insight-label">服务费收入</span>
            </div>
            <div class="insight-item">
              <span class="insight-val">{{ revenue.paidSessions }}</span>
              <span class="insight-label">已支付订单</span>
            </div>
          </div>
          <div v-else class="insight-empty">暂无收入数据</div>
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
import { getChargingVolumeApi, getRevenueApi } from '@/api/admin/report'
import { POLLING_INTERVAL } from '@/utils/constants'

const loading = ref(false)
const rawStations = ref<any[]>([])
const stationDetails = ref<any[]>([])
const volume = ref<any>(null)
const revenue = ref<any>(null)

let pollingTimer: ReturnType<typeof setInterval> | null = null

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
    { label: '充电桩总数', value: String(total), sub: `运行中 ${running} / 停止 ${total - running}`, color: '#1A1A1A' },
    { label: '正在充电', value: String(charging), sub: '所有桩合计', color: '#16A34A' },
    { label: '排队等待', value: String(queueing), sub: `${rawStations.value.filter(s => s.queueCount > 0).length} 个桩有排队`, color: '#D97706' },
    { label: '收入(已支付)', value: revenue.value ? `¥${revenue.value.totalRevenue}` : '--', sub: `电费 ¥${revenue.value?.electricityRevenue || 0}`, color: '#2563EB' },
  ]
})

const stationData = computed(() => {
  if (stationDetails.value.length > 0) return stationDetails.value
  return rawStations.value.map((s: any) => ({
    ...s, queueList: [], waitingList: [], chargingList: [],
  }))
})

async function fetchData(silent = false) {
  if (!silent) loading.value = true
  try {
    const [staRes, volRes, revRes] = await Promise.all([
      getStationsApi(),
      getChargingVolumeApi(),
      getRevenueApi(),
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

    volume.value = (volRes.data as any).data
    revenue.value = (revRes.data as any).data
  } catch {
    if (!silent) ElMessage.error('获取数据失败，请检查后端是否运行')
    rawStations.value = []
    stationDetails.value = []
  } finally { loading.value = false }
}

onMounted(() => { fetchData(); startPolling() })
onUnmounted(stopPolling)
</script>

<style scoped>
.admin-dashboard { display: flex; flex-direction: column; gap: 20px; }
.metrics-row { margin-bottom: 0 !important; }
.metric-card { border-radius: 10px; text-align: center; }
.metric-label { font-size: 13px; color: #64748B; margin-bottom: 6px; }
.metric-value { font-size: 32px; font-weight: 700; font-family: 'JetBrains Mono', monospace; line-height: 1.1; }
.metric-sub { font-size: 12px; color: #94A3B8; margin-top: 4px; }
.section-card { border-radius: 10px; }
.section-title { font-size: 16px; font-weight: 600; color: #1E293B; display: flex; justify-content: space-between; align-items: center; }
.station-block { padding: 16px 0; border-bottom: 1px solid #F1F5F9; }
.station-block:last-child { border-bottom: none; }
.station-block-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.station-block-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.station-name { font-size: 16px; font-weight: 600; color: #1E293B; }
.station-metrics { font-size: 12px; color: #64748B; font-family: 'JetBrains Mono', monospace; }
.zone-tables { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.zone-col { background: #F8FAFC; border-radius: 8px; overflow: hidden; }
.zone-col-header { font-size: 13px; font-weight: 600; padding: 8px 12px; background: #FFFFFF; border-left: 3px solid; border-bottom: 1px solid #E2E8F0; }
.zone-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.zone-table thead th { padding: 6px 8px; text-align: left; color: #94A3B8; font-weight: 500; border-bottom: 1px solid #E2E8F0; }
.zone-table tbody td { padding: 6px 8px; border-bottom: 1px solid #F1F5F9; color: #334155; }
.zone-table tbody tr:last-child td { border-bottom: none; }
.zone-empty { padding: 24px; text-align: center; color: #94A3B8; font-size: 13px; }

/* 统计概览 */
.insight-grid { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.insight-item { display: flex; flex-direction: column; align-items: center; min-width: 100px; padding: 12px 16px; background: #F8FAFC; border-radius: 8px; flex: 1; }
.insight-val { font-size: 20px; font-weight: 700; color: #1E293B; font-family: 'JetBrains Mono', monospace; }
.insight-label { font-size: 12px; color: #94A3B8; margin-top: 4px; }
.insight-empty { text-align: center; padding: 32px; color: #94A3B8; font-size: 14px; }
</style>
