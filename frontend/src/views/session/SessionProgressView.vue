<template>
  <div class="session-progress" v-if="session">
    <!-- 顶部状态 -->
    <div class="progress-header">
      <el-button text @click="goBack"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <ChargingStatusBadge :status="session.status" />
    </div>

    <!-- ═══════ 排队中 ═══════ -->
    <template v-if="session.status === 'queued'">
      <el-card shadow="never" class="status-card">
        <div class="queue-display">
          <div class="queue-number">{{ session.queuePosition }}</div>
          <p class="queue-label">排队位置</p>
        </div>
        <div class="queue-info">
          <p><strong>{{ session.station?.name }}</strong></p>
          <p class="info-text">预估等待 {{ session.estimatedWaitMinutes || '--' }} 分钟</p>
        </div>
      </el-card>

      <div class="action-row">
        <el-button @click="showSwitchDialog = true" :disabled="!switchOptions.length">换队</el-button>
        <el-button type="danger" plain @click="handleCancel">取消排队</el-button>
      </div>
    </template>

    <!-- ═══════ 等待中 ═══════ -->
    <template v-else-if="session.status === 'waiting'">
      <el-card shadow="never" class="status-card waiting-card">
        <el-icon :size="40" color="#3B82F6"><Clock /></el-icon>
        <p class="waiting-title">即将进入充电区</p>
        <p class="info-text">{{ session.station?.name }}</p>
      </el-card>
      <div class="action-row">
        <el-button type="danger" plain @click="handleCancel">退出充电（收基础服务费）</el-button>
      </div>
    </template>

    <!-- ═══════ 充电中 ═══════ -->
    <template v-else-if="session.status === 'charging'">
      <el-card shadow="never" class="status-card charging-card">
        <el-progress type="circle" :percentage="session.progress || 0" :width="120" :stroke-width="8" color="#16A34A" />
        <div class="charging-info">
          <p class="charging-energy">{{ session.chargedEnergyKwh }} / {{ session.requestedEnergyKwh }} kWh</p>
          <p class="info-text">充电时长 {{ session.chargingDuration || '00:00:00' }}</p>
          <p class="info-text">协议：{{ session.protocol?.name || '--' }}</p>
        </div>
      </el-card>
    </template>

    <!-- ═══════ 已完成/已取消 ═══════ -->
    <template v-else-if="session.status === 'completed' || session.status === 'cancelled'">
      <el-result :icon="session.status === 'completed' ? 'success' : 'info'"
        :title="session.status === 'completed' ? '充电完成' : '已取消'"
        :sub-title="session.bill ? `总费用 ¥${session.bill.totalFee}` : '无费用'">
        <template #extra>
          <el-button v-if="session.bill" type="primary" @click="goToBill(session.bill.billId)">查看账单</el-button>
          <el-button @click="goHome">返回主页</el-button>
        </template>
      </el-result>
    </template>

    <!-- ═══════ 换队对话框 ═══════ -->
    <el-dialog v-model="showSwitchDialog" title="选择目标充电桩" :width="480" @open="loadSwitchOptions">
      <el-radio-group v-model="targetStationId" class="switch-options">
        <el-radio v-for="opt in switchOptions" :key="opt.id" :value="opt.id" class="switch-option" border>
          <div class="option-content">
            <div class="option-header">
              <strong>{{ opt.name }}</strong>
              <span class="option-wait">约 {{ opt.estimatedWaitMinutes }} 分钟</span>
            </div>
            <div class="option-metrics">
              <span>🚶排队 {{ opt.queueCount }}/{{ opt.queueCapacity }}</span>
              <span>⏳等待 {{ opt.waitingCount }}/{{ opt.waitingCapacity }}</span>
              <span>⚡充电 {{ opt.chargingCount }}/{{ opt.chargingCapacity }}</span>
            </div>
            <div class="option-protocols">
              <el-tag v-for="p in opt.supportedProtocols" :key="p.id" size="small" effect="plain" class="proto-tag">
                {{ p.name }}
              </el-tag>
            </div>
          </div>
        </el-radio>
      </el-radio-group>
      <div v-if="!switchOptions.length" class="no-options">
        暂无可换入的充电桩
      </div>
      <template #footer>
        <el-button @click="showSwitchDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!targetStationId" @click="handleSwitch">确认更换</el-button>
      </template>
    </el-dialog>
  </div>

  <div v-else-if="loading" class="loading-wrapper">
    <el-skeleton :rows="4" animated />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Clock } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ChargingStatusBadge from '@/components/ChargingStatusBadge.vue'
import {
  getSessionDetailApi,
  getSwitchOptionsApi,
  switchStationApi,
  cancelSessionApi,
} from '@/api/session'
import { getStationsApi } from '@/api/station'
import { POLLING_INTERVAL } from '@/utils/constants'

const route = useRoute()
const router = useRouter()

const session = ref<any>(null)
const loading = ref(true)
const showSwitchDialog = ref(false)
const switchOptions = ref<any[]>([])
const targetStationId = ref<number | null>(null)

let pollingTimer: ReturnType<typeof setTimeout> | null = null

async function fetchSession() {
  const id = Number(route.params.id)
  if (!id) return
  try {
    const res = await getSessionDetailApi(id)
    const body = res.data as any
    session.value = body.data

    // 终端状态停止轮询
    if (['completed', 'cancelled'].includes(body.data.status)) {
      stopPolling()
    }
  } catch (err: any) {
    if (err?.response?.status === 403 || err?.response?.status === 404) {
      stopPolling()
      ElMessage.error('会话不存在或无权访问')
      router.push('/')
    }
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollingTimer = setInterval(() => {
    fetchSession()
  }, POLLING_INTERVAL)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

async function loadSwitchOptions() {
  try {
    // 获取所有充电桩详情（含排队时间、协议）
    const res = await getStationsApi()
    const body = res.data as any
    const allStations = body.data?.stations || []
    const currentStationId = session.value?.station?.id
    // 过滤掉当前桩，只保留 running 的
    switchOptions.value = allStations.filter((s: any) =>
      s.id !== currentStationId && s.status === 'running'
    )
  } catch {
    switchOptions.value = []
  }
}

async function handleSwitch() {
  if (!targetStationId.value) return
  const id = Number(route.params.id)
  try {
    await switchStationApi(id, targetStationId.value)
    ElMessage.success('已更换到目标充电桩')
    showSwitchDialog.value = false
    fetchSession()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '换队失败')
  }
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm(
      session.value.status === 'queued'
        ? '确定要取消排队吗？当前免费取消'
        : '确定要退出充电吗？将收取基础服务费',
      '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' },
    )
    const id = Number(route.params.id)
    const res = await cancelSessionApi(id)
    const body = res.data as any
    ElMessage.success(body.message || '已取消')
    stopPolling()
    fetchSession()
  } catch (err: any) {
    if (err?.code !== 'cancel') {
      ElMessage.error(err?.response?.data?.message || '取消失败')
    }
  }
}

function goBack() { router.back() }
function goHome() { router.push('/') }
function goToBill(billId: number) { router.push(`/bills/${billId}`) }

onMounted(() => {
  fetchSession().then(() => {
    if (session.value && ['queued', 'waiting', 'charging'].includes(session.value.status)) {
      startPolling()
    }
  })
  loadSwitchOptions()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.session-progress {
  max-width: 520px;
  margin: 0 auto;
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

/* 排队 */
.status-card {
  border-radius: 12px;
  text-align: center;
  padding: 24px;
}

.queue-display {
  margin-bottom: 16px;
}

.queue-number {
  font-size: 72px;
  font-weight: 700;
  color: #2563EB;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1;
}

.queue-label {
  font-size: 16px;
  color: #64748B;
  margin-top: 4px;
}

.queue-info p {
  margin: 4px 0;
}

.info-text {
  font-size: 14px;
  color: #94A3B8;
}

/* 等待 */
.waiting-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 24px;
}

.waiting-title {
  font-size: 18px;
  font-weight: 600;
  color: #1E293B;
}

/* 充电中 */
.charging-card {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 32px 24px;
}

.charging-info {
  text-align: left;
}

.charging-energy {
  font-size: 20px;
  font-weight: 600;
  color: #16A34A;
  font-family: 'JetBrains Mono', monospace;
}

/* 操作按钮 */
.action-row {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}

/* 换队选项 */
.switch-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.switch-option {
  display: flex;
  width: 100%;
  align-items: flex-start;
  padding: 12px 16px;
  height: auto !important;
  border-radius: 8px;
  margin-right: 0;
}

.switch-option :deep(.el-radio__label) {
  width: 100%;
}

.option-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.option-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.option-header strong {
  font-size: 15px;
  color: #1E293B;
}

.option-wait {
  font-size: 13px;
  color: #D97706;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.option-metrics {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #64748B;
  font-family: 'JetBrains Mono', monospace;
}

.option-protocols {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.proto-tag {
  font-size: 11px;
}

.no-options {
  text-align: center;
  padding: 24px;
  color: #94A3B8;
  font-size: 14px;
}

.loading-wrapper {
  padding: 48px;
}
</style>
