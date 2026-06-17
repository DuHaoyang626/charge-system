<template>
  <div class="session-progress" v-if="session">
    <div class="progress-header">
      <el-button text @click="goBack"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <ChargingStatusBadge :status="session.status" />
    </div>

    <!-- queued -->
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

      <!-- advanceReady：排队→等待 确认卡片 -->
      <el-card v-if="session.advanceReady" shadow="never" class="status-card waiting-card">
        <el-icon :size="40" color="#3B82F6"><Clock /></el-icon>
        <p class="waiting-title">即将进入等待区，请确认充电信息</p>
        <p class="info-text">{{ session.station?.name }}</p>

        <div class="protocol-section" v-if="waitingProtocols.length">
          <p class="section-label">选择充电协议</p>
          <el-radio-group v-model="selectedWaitingProtocol" class="waiting-protocols">
            <el-radio v-for="p in waitingProtocols" :key="p.id" :value="p.id" border class="waiting-proto-option">
              <div class="proto-option-content">
                <strong>{{ p.name }}</strong>
                <span class="proto-power">{{ p.powerKw }}kW</span>
              </div>
            </el-radio>
          </el-radio-group>
        </div>

        <div class="fee-preview">基础服务费 <strong>¥{{ session.currentFee?.baseServiceFee || '5.00' }}</strong></div>
      </el-card>

      <div class="action-row" v-if="!session.advanceReady">
        <el-button @click="showSwitchDialog = true" :disabled="!switchOptions.length">换队</el-button>
        <el-button type="danger" plain @click="handleCancel">取消排队</el-button>
      </div>
      <div class="action-row" v-else>
        <el-button type="primary" size="large" @click="handleConfirmCharging" :loading="confirmLoading">
          确认进入等待区
        </el-button>
        <el-button type="danger" plain @click="handleRejectConfirm">退出</el-button>
      </div>
    </template>

    <!-- waiting -->
    <template v-else-if="session.status === 'waiting'">
      <!-- advanceReady=true：显示充电确认 -->
      <template v-if="session.advanceReady">
        <el-card shadow="never" class="status-card waiting-card">
          <el-icon :size="40" color="#3B82F6"><Clock /></el-icon>
          <p class="waiting-title">即将进入充电区，请确认充电</p>
          <p class="info-text">{{ session.station?.name }}</p>

          <!-- 协议选择 -->
          <div class="protocol-section" v-if="waitingProtocols.length">
            <p class="section-label">选择充电协议</p>
            <el-radio-group v-model="selectedWaitingProtocol" class="waiting-protocols">
              <el-radio v-for="p in waitingProtocols" :key="p.id" :value="p.id" border class="waiting-proto-option">
                <div class="proto-option-content">
                  <strong>{{ p.name }}</strong>
                  <span class="proto-power">{{ p.powerKw }}kW</span>
                </div>
              </el-radio>
            </el-radio-group>
          </div>

          <div class="fee-preview">基础服务费 <strong>¥{{ session.currentFee?.baseServiceFee || '5.00' }}</strong></div>
        </el-card>
        <div class="action-row">
          <el-button type="primary" size="large" @click="handleConfirmCharging" :loading="confirmLoading">
            确认开始充电
          </el-button>
          <el-button type="danger" plain @click="handleCancel">退出（收基础服务费）</el-button>
        </div>
      </template>
      <!-- advanceReady=false：等待调度 -->
      <template v-else>
        <el-card shadow="never" class="status-card waiting-card">
          <el-icon :size="40" color="#94A3B8"><Clock /></el-icon>
          <p class="waiting-title">等待充电位</p>
          <p class="info-text">{{ session.station?.name }}</p>
          <div class="fee-preview">基础服务费 <strong>¥{{ session.currentFee?.baseServiceFee || '5.00' }}</strong></div>
        </el-card>
        <div class="action-row">
          <el-button type="danger" plain @click="handleCancel">退出（收基础服务费）</el-button>
        </div>
      </template>
    </template>

    <!-- charging -->
    <template v-else-if="session.status === 'charging'">
      <el-card shadow="never" class="charging-main">
        <div class="charging-left">
          <el-progress type="circle" :percentage="session.progress || 0" :width="120" :stroke-width="8" color="#16A34A" />
        </div>
        <div class="charging-right">
          <div class="charging-energy">{{ session.chargedEnergyKwh }} / {{ session.requestedEnergyKwh }} kWh</div>
          <div class="info-text">充电时长 {{ session.chargingDuration || '00:00:00' }}</div>
          <div class="info-text">协议：{{ session.protocol?.name || '--' }}（{{ session.protocol?.powerKw || '--' }}kW）</div>
          <div class="info-text" v-if="session.estimatedEndTime">预计结束：{{ formatTime(session.estimatedEndTime) }}</div>
        </div>
      </el-card>
      <el-card shadow="never" class="fee-card">
        <template #header>实时费用</template>
        <div class="fee-row"><span>电费</span><span class="fee-value">¥{{ session.currentFee?.electricityFee?.toFixed(2) || '0.00' }}</span></div>
        <div class="fee-row"><span>服务费</span><span class="fee-value">¥{{ session.currentFee?.totalServiceFee?.toFixed(2) || '0.00' }}</span></div>
        <el-divider />
        <div class="fee-row total"><span>合计</span><span class="fee-total">¥{{ session.currentFee?.totalFee?.toFixed(2) || '0.00' }}</span></div>
      </el-card>
      <div class="action-row charging-actions">
        <el-button @click="openEnergyDialog">修改电量</el-button>
        <el-button @click="openProtocolDialog">切换协议</el-button>
        <el-button type="danger" @click="handleStopCharging">停止充电</el-button>
      </div>
    </template>

    <!-- completed / cancelled -->
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

    <!-- 换队对话框 -->
    <el-dialog v-model="showSwitchDialog" title="选择目标充电桩" :width="480" @open="loadSwitchOptions">
      <el-radio-group v-model="targetStationId" class="switch-options">
        <el-radio v-for="opt in switchOptions" :key="opt.id" :value="opt.id" class="switch-option" border>
          <div class="option-content">
            <div class="option-header"><strong>{{ opt.name }}</strong><span class="option-wait">约 {{ opt.estimatedWaitMinutes }} 分钟</span></div>
            <div class="option-metrics">
              <span>🚶排队 {{ opt.queueCount }}/{{ opt.queueCapacity }}</span>
              <span>⏳等待 {{ opt.waitingCount }}/{{ opt.waitingCapacity }}</span>
              <span>⚡充电 {{ opt.chargingCount }}/{{ opt.chargingCapacity }}</span>
            </div>
            <div class="option-protocols">
              <el-tag v-for="p in opt.supportedProtocols" :key="p.id" size="small" effect="plain" class="proto-tag">{{ p.name }}</el-tag>
            </div>
          </div>
        </el-radio>
      </el-radio-group>
      <div v-if="!switchOptions.length" class="no-options">暂无可换入的充电桩</div>
      <template #footer>
        <el-button @click="showSwitchDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!targetStationId" @click="handleSwitch">确认更换</el-button>
      </template>
    </el-dialog>

    <!-- 修改电量对话框 -->
    <el-dialog v-model="showEnergyDialog" title="修改目标电量" :width="400">
      <el-form label-position="top">
        <el-form-item label="新目标电量 (kWh)">
          <el-input-number v-model="newEnergyValue" :min="minEnergy" :max="maxEnergy" :precision="1" :step="5" style="width: 100%" />
        </el-form-item>
        <div class="form-tip">当前已充电量 {{ session.chargedEnergyKwh }} kWh，最少 {{ minEnergy }} kWh</div>
      </el-form>
      <template #footer>
        <el-button @click="showEnergyDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!newEnergyValue || newEnergyValue < minEnergy" @click="handleUpdateEnergy">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 切换协议对话框（单选框） -->
    <el-dialog v-model="showProtocolDialog" title="切换充电协议" :width="420">
      <p class="dialog-hint">选择当前充电桩支持的协议</p>
      <el-radio-group v-model="selectedProtocolId" class="protocol-radios">
        <el-radio v-for="opt in protocolOptions" :key="opt.id" :value="opt.id" border class="protocol-radio">
          <div class="protocol-radio-content">
            <strong>{{ opt.name }}</strong>
            <span class="protocol-power">{{ opt.powerKw }}kW</span>
          </div>
        </el-radio>
      </el-radio-group>
      <div v-if="!protocolOptions.length" class="no-options">无可用协议</div>
      <template #footer>
        <el-button @click="showProtocolDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedProtocolId" @click="handleUpdateProtocol">切换到此协议</el-button>
      </template>
    </el-dialog>
  </div>

  <div v-else-if="loading" class="loading-wrapper">
    <el-skeleton :rows="4" animated />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Clock } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ChargingStatusBadge from '@/components/ChargingStatusBadge.vue'
import {
  getSessionDetailApi, getSwitchOptionsApi, switchStationApi,
  cancelSessionApi, confirmChargingApi, updateEnergyApi,
  getProtocolOptionsApi, updateProtocolApi, stopChargingApi,
} from '@/api/session'
import { getStationsApi } from '@/api/station'
import { POLLING_INTERVAL } from '@/utils/constants'
import { formatTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const session = ref<any>(null)
const loading = ref(true)
let pollingTimer: ReturnType<typeof setInterval> | null = null

// 换队
const showSwitchDialog = ref(false)
const switchOptions = ref<any[]>([])
const targetStationId = ref<number | null>(null)

// 电量
const showEnergyDialog = ref(false)
const newEnergyValue = ref(0)
const minEnergy = computed(() => Math.max(0.1, (session.value?.chargedEnergyKwh || 0) + 0.1))
const maxEnergy = ref(200)

// 协议（单选框）
const showProtocolDialog = ref(false)
const protocolOptions = ref<any[]>([])
const selectedProtocolId = ref<number | null>(null)

// 等待区确认充电
const waitingProtocols = ref<any[]>([])
const selectedWaitingProtocol = ref<number | null>(null)
const confirmLoading = ref(false)
const protocolsLoaded = ref(false)

async function loadWaitingProtocols() {
  if (protocolsLoaded.value) return
  protocolsLoaded.value = true
  try {
    const res = await getProtocolOptionsApi(Number(route.params.id))
    const body = res.data as any
    waitingProtocols.value = body.data?.options || []
    if (waitingProtocols.value.length > 0) {
      selectedWaitingProtocol.value = waitingProtocols.value[0].id
    }
  } catch { waitingProtocols.value = [] }
}

// advanceReady 变 false 时重置加载标记，下次变 true 时重新加载
watch(() => session.value?.advanceReady, (val) => {
  if (val === false) protocolsLoaded.value = false
})

async function handleConfirmCharging() {
  if (!selectedWaitingProtocol.value) {
    ElMessage.warning('请选择充电协议')
    return
  }
  confirmLoading.value = true
  try {
    await confirmChargingApi(Number(route.params.id), {
      action: 'confirm',
      protocolId: selectedWaitingProtocol.value,
    })
    ElMessage.success('开始充电')
    fetchSession()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '确认失败')
  } finally { confirmLoading.value = false }
}

async function handleRejectConfirm() {
  try {
    await ElMessageBox.confirm(
      '确定退出？将根据当前状态收取相应费用',
      '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const res = await confirmChargingApi(Number(route.params.id), { action: 'reject' })
    ElMessage.success((res.data as any).message || '已退出')
    stopPolling(); fetchSession()
  } catch (err: any) {
    if (err?.code !== 'cancel') ElMessage.error(err?.response?.data?.message || '操作失败')
  }
}

// ── 轮询 ──
async function fetchSession() {
  const id = Number(route.params.id)
  if (!id) return
  try {
    const res = await getSessionDetailApi(id)
    const body = res.data as any
    session.value = body.data
    if (['completed', 'cancelled'].includes(body.data.status)) stopPolling()
    if (body.data.advanceReady) loadWaitingProtocols()
  } catch (err: any) {
    if (err?.response?.status === 403 || err?.response?.status === 404) {
      stopPolling(); ElMessage.error('会话不存在或无权访问'); router.push('/')
    }
  } finally { loading.value = false }
}

function startPolling() { stopPolling(); pollingTimer = setInterval(fetchSession, POLLING_INTERVAL) }
function stopPolling() { if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null } }

// ── 换队 ──
async function loadSwitchOptions() {
  try {
    const res = await getStationsApi()
    const body = res.data as any
    const all = body.data?.stations || []
    const curId = session.value?.station?.id
    switchOptions.value = all.filter((s: any) => s.id !== curId && s.status === 'running')
  } catch { switchOptions.value = [] }
}

async function handleSwitch() {
  if (!targetStationId.value) return
  try {
    await switchStationApi(Number(route.params.id), targetStationId.value)
    ElMessage.success('已更换到目标充电桩'); showSwitchDialog.value = false; fetchSession()
  } catch (err: any) { ElMessage.error(err?.response?.data?.message || '换队失败') }
}

// ── 取消 ──
async function handleCancel() {
  try {
    await ElMessageBox.confirm(
      session.value.status === 'queued' ? '确定取消排队？免费取消' : '确定退出？将收取基础服务费',
      '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const res = await cancelSessionApi(Number(route.params.id))
    ElMessage.success((res.data as any).message || '已取消')
    stopPolling(); fetchSession()
  } catch (err: any) { if (err?.code !== 'cancel') ElMessage.error(err?.response?.data?.message || '取消失败') }
}

// ── 修改电量 ──
function openEnergyDialog() { newEnergyValue.value = session.value?.requestedEnergyKwh || 60; showEnergyDialog.value = true }

async function handleUpdateEnergy() {
  try {
    await updateEnergyApi(Number(route.params.id), newEnergyValue.value)
    ElMessage.success('目标电量已更新'); showEnergyDialog.value = false; fetchSession()
  } catch (err: any) { ElMessage.error(err?.response?.data?.message || '修改失败') }
}

// ── 切换协议（单选框） ──
async function openProtocolDialog() {
  try {
    const res = await getProtocolOptionsApi(Number(route.params.id))
    const body = res.data as any
    protocolOptions.value = body.data?.options || []
    selectedProtocolId.value = session.value?.protocol?.id || null
    showProtocolDialog.value = true
  } catch { ElMessage.error('获取协议列表失败') }
}

async function handleUpdateProtocol() {
  if (!selectedProtocolId.value) return
  try {
    await updateProtocolApi(Number(route.params.id), [selectedProtocolId.value])
    ElMessage.success('已切换到所选协议'); showProtocolDialog.value = false; fetchSession()
  } catch (err: any) { ElMessage.error(err?.response?.data?.message || '切换失败') }
}

// ── 停止充电 ──
async function handleStopCharging() {
  try {
    await ElMessageBox.confirm(
      `确定停止充电？已充电量 ${session.value?.chargedEnergyKwh} kWh，将按实际用量计费`,
      '停止充电', { confirmButtonText: '确定停止', cancelButtonText: '取消', type: 'warning' })
    const res = await stopChargingApi(Number(route.params.id))
    ElMessage.success('充电已结束'); stopPolling(); fetchSession()
  } catch (err: any) { if (err?.code !== 'cancel') ElMessage.error(err?.response?.data?.message || '停止失败') }
}

function goBack() { router.back() }
function goHome() { router.push('/') }
function goToBill(id: number) { router.push(`/bills/${id}`) }

onMounted(() => {
  fetchSession().then(() => {
    if (session.value && ['queued', 'waiting', 'charging'].includes(session.value.status)) startPolling()
  })
})
onUnmounted(() => { stopPolling() })
</script>

<style scoped>
.session-progress { max-width: 520px; margin: 0 auto; }
.progress-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.status-card { border-radius: 12px; text-align: center; padding: 24px; }
.queue-display { margin-bottom: 16px; }
.queue-number { font-size: 72px; font-weight: 700; color: #2563EB; font-family: 'JetBrains Mono', monospace; line-height: 1; }
.queue-label { font-size: 16px; color: #64748B; margin-top: 4px; }
.queue-info p { margin: 4px 0; }
.info-text { font-size: 14px; color: #94A3B8; }
.waiting-card { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 24px; }
.waiting-title { font-size: 18px; font-weight: 600; color: #1E293B; }
.fee-preview { font-size: 13px; color: #64748B; }
.charging-main { border-radius: 12px; display: flex; align-items: center; gap: 24px; padding: 32px 24px; }
.charging-left { flex-shrink: 0; }
.charging-right { display: flex; flex-direction: column; gap: 4px; }
.charging-energy { font-size: 20px; font-weight: 600; color: #16A34A; font-family: 'JetBrains Mono', monospace; }
.fee-card { border-radius: 12px; margin-top: 16px; }
.fee-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 14px; color: #475569; }
.fee-value { font-family: 'JetBrains Mono', monospace; color: #1E293B; }
.fee-row.total { font-size: 16px; font-weight: 600; }
.fee-total { color: #EA580C; font-size: 20px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.action-row { display: flex; justify-content: center; gap: 12px; margin-top: 20px; flex-wrap: wrap; }
.charging-actions { display: flex; gap: 8px; }

/* 换队 */
.switch-options { display: flex; flex-direction: column; gap: 12px; width: 100%; }
.switch-option { display: flex; width: 100%; align-items: flex-start; padding: 12px 16px; height: auto !important; border-radius: 8px; margin-right: 0; }
.switch-option :deep(.el-radio__label) { width: 100%; }
.option-content { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.option-header { display: flex; justify-content: space-between; align-items: center; }
.option-header strong { font-size: 15px; color: #1E293B; }
.option-wait { font-size: 13px; color: #D97706; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.option-metrics { display: flex; gap: 12px; font-size: 12px; color: #64748B; font-family: 'JetBrains Mono', monospace; }
.option-protocols { display: flex; flex-wrap: wrap; gap: 4px; }
.proto-tag { font-size: 11px; }
.no-options { text-align: center; padding: 24px; color: #94A3B8; font-size: 14px; }
.form-tip { font-size: 12px; color: #94A3B8; margin-top: 4px; }

/* 协议切换（单选框） */
.dialog-hint { font-size: 13px; color: #64748B; margin-bottom: 12px; }
.protocol-radios { display: flex; flex-direction: column; gap: 8px; width: 100%; }
.protocol-radio { width: 100%; margin-right: 0; padding: 10px 12px; border-radius: 8px; }
.protocol-radio-content { display: flex; justify-content: space-between; align-items: center; }
.protocol-radio-content strong { font-size: 15px; }
.protocol-power { font-size: 13px; color: #64748B; font-family: 'JetBrains Mono', monospace; }

/* 等待区确认充电 */
.protocol-section { width: 100%; margin-top: 12px; }
.section-label { font-size: 13px; color: #475569; margin-bottom: 8px; text-align: left; }
.waiting-protocols { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.waiting-proto-option { width: 100%; margin-right: 0; padding: 8px 12px; border-radius: 6px; }
.proto-option-content { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.proto-option-content strong { font-size: 14px; color: #1E293B; }

.loading-wrapper { padding: 48px; }
</style>
