<template>
  <div class="session-progress" v-if="session">
    <div class="progress-header">
      <button class="btn-glass btn-glass-sm" @click="goBack">← 返回</button>
      <ChargingStatusBadge :status="session.status" />
    </div>

    <!-- queued -->
    <template v-if="session.status === 'queued'">
      <div class="glass-card status-card">
        <div class="queue-display">
          <div class="queue-number">{{ session.queuePosition }}</div>
          <p class="queue-label">排队位置</p>
          <div class="queue-info">
            <p><strong>{{ session.station?.name }}</strong></p>
            <p class="info-text">预估等待 {{ session.estimatedWaitMinutes || '--' }} 分钟</p>
          </div>
        </div>
      </div>

      <div class="glass-card waiting-card" v-if="session.advanceReady">
        <div class="waiting-icon">⏳</div>
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
      </div>

      <div class="action-row" v-if="!session.advanceReady">
        <button class="btn-glass" @click="showSwitchDialog = true" :disabled="!switchOptions.length">🔄 换队</button>
        <button class="btn-glass btn-glass-danger" @click="handleCancel">✕ 取消排队</button>
      </div>
      <div class="action-row" v-else>
        <button class="btn-glass btn-glass-primary btn-glass-lg" @click="handleConfirmCharging" :disabled="confirmLoading">
          {{ confirmLoading ? '⏳ 确认中...' : '✅ 确认进入等待区' }}
        </button>
        <button class="btn-glass btn-glass-danger" @click="handleRejectConfirm">退出</button>
      </div>
    </template>

    <!-- waiting -->
    <template v-else-if="session.status === 'waiting'">
      <template v-if="session.advanceReady">
        <div class="glass-card waiting-card">
          <div class="waiting-icon">⏳</div>
          <p class="waiting-title">即将进入充电区，请确认充电</p>
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
        </div>
        <div class="action-row">
          <button class="btn-glass btn-glass-primary btn-glass-lg" @click="handleConfirmCharging" :disabled="confirmLoading">
            {{ confirmLoading ? '⏳ 确认中...' : '⚡ 确认开始充电' }}
          </button>
          <button class="btn-glass btn-glass-danger" @click="handleCancel">退出（收基础服务费）</button>
        </div>
      </template>
      <template v-else>
        <div class="glass-card waiting-card">
          <div class="waiting-icon">⏳</div>
          <p class="waiting-title">等待充电位</p>
          <p class="info-text">{{ session.station?.name }}</p>
          <div class="fee-preview">基础服务费 <strong>¥{{ session.currentFee?.baseServiceFee || '5.00' }}</strong></div>
        </div>
        <div class="action-row">
          <button class="btn-glass btn-glass-danger" @click="handleCancel">退出（收基础服务费）</button>
        </div>
      </template>
    </template>

    <!-- charging -->
    <template v-else-if="session.status === 'charging'">
      <div class="charging-info-row">
        <div class="glass-card charging-main">
          <el-progress type="circle" :percentage="session.progress || 0" :width="clampWidth" :stroke-width="8" color="#22C55E" />
          <div class="charging-right">
            <div class="charging-energy">
              <span class="energy-val">{{ session.chargedEnergyKwh?.toFixed(1) }}</span>
              <span class="energy-sep">/</span>
              <span class="energy-target">{{ session.requestedEnergyKwh }} kWh</span>
            </div>
            <div class="charging-duration">⏱ {{ session.chargingDuration || '00:00:00' }}</div>
            <div class="info-text">协议：{{ session.protocol?.name || '--' }}（{{ session.protocol?.powerKw || '--' }}kW）</div>
            <div class="info-text" v-if="session.estimatedEndTime">预计结束：{{ formatTime(session.estimatedEndTime) }}</div>
          </div>
        </div>

        <div class="glass-card fee-card">
          <div class="fee-header">💰 实时费用</div>
          <div class="fee-row"><span>电费</span><span class="fee-value">¥{{ session.currentFee?.electricityFee?.toFixed(2) || '0.00' }}</span></div>
          <div class="fee-row"><span>服务费</span><span class="fee-value">¥{{ session.currentFee?.totalServiceFee?.toFixed(2) || '0.00' }}</span></div>
          <el-divider style="margin:6px 0;border-color:var(--border-light);" />
          <div class="fee-row total"><span>合计</span><span class="fee-total">¥{{ session.currentFee?.totalFee?.toFixed(2) || '0.00' }}</span></div>
        </div>
      </div>

      <div class="action-row charging-actions">
        <button class="btn-glass" @click="openEnergyDialog">📊 修改电量</button>
        <button class="btn-glass" @click="openProtocolDialog">🔄 切换协议</button>
        <button class="btn-glass btn-glass-danger" @click="handleStopCharging">⏹ 停止充电</button>
      </div>
    </template>

    <!-- completed / cancelled -->
    <template v-else-if="session.status === 'completed' || session.status === 'cancelled'">
      <div class="glass-card result-card">
        <div class="result-icon">{{ session.status === 'completed' ? '✅' : 'ℹ️' }}</div>
        <h3>{{ session.status === 'completed' ? '充电完成' : '已取消' }}</h3>
        <p class="result-text">{{ session.bill ? `总费用 ¥${session.bill.totalFee}` : '无费用' }}</p>
        <div class="action-row">
          <button v-if="session.bill" class="btn-glass btn-glass-primary" @click="goToBill(session.bill.billId)">📋 查看账单</button>
          <button class="btn-glass" @click="goHome">🏠 返回主页</button>
        </div>
      </div>
    </template>

    <!-- 换队对话框 -->
    <el-dialog v-model="showSwitchDialog" title="选择目标充电桩" :width="480" @open="loadSwitchOptions" class="glass-dialog">
      <el-radio-group v-model="targetStationId" class="switch-options">
        <el-radio v-for="opt in switchOptions" :key="opt.id" :value="opt.id" class="switch-option" border>
          <div class="option-content">
            <div class="option-header">
              <strong>{{ opt.name }}</strong>
              <span class="option-wait glass-badge">⏱ ~{{ opt.estimatedWaitMinutes }}分</span>
            </div>
            <div class="option-metrics">
              <span>🚶{{ opt.queueCount }}/{{ opt.queueCapacity }}</span>
              <span>⏳{{ opt.waitingCount }}/{{ opt.waitingCapacity }}</span>
              <span>⚡{{ opt.chargingCount }}/{{ opt.chargingCapacity }}</span>
            </div>
            <div class="option-protocols">
              <el-tag v-for="p in opt.supportedProtocols" :key="p.id" size="small" effect="plain" class="glass-badge">{{ p.name }}</el-tag>
            </div>
          </div>
        </el-radio>
      </el-radio-group>
      <div v-if="!switchOptions.length" class="no-options">暂无可换入的充电桩</div>
      <template #footer>
        <button class="btn-glass btn-glass-sm" @click="showSwitchDialog = false">取消</button>
        <button class="btn-glass btn-glass-primary btn-glass-sm" :disabled="!targetStationId" @click="handleSwitch">确认更换</button>
      </template>
    </el-dialog>

    <!-- 修改电量对话框 -->
    <el-dialog v-model="showEnergyDialog" title="修改目标电量" :width="400" class="glass-dialog">
      <el-form label-position="top">
        <el-form-item label="新目标电量 (kWh)">
          <el-input-number v-model="newEnergyValue" :min="minEnergy" :max="maxEnergy" :precision="1" :step="5" style="width:100%" />
        </el-form-item>
        <div class="form-tip" style="font-size:12px;color:var(--text-tertiary);">当前已充电量 {{ session.chargedEnergyKwh }} kWh，最少 {{ minEnergy }} kWh</div>
      </el-form>
      <template #footer>
        <button class="btn-glass btn-glass-sm" @click="showEnergyDialog = false">取消</button>
        <button class="btn-glass btn-glass-primary btn-glass-sm" :disabled="!newEnergyValue || newEnergyValue < minEnergy" @click="handleUpdateEnergy">确认修改</button>
      </template>
    </el-dialog>

    <!-- 切换协议对话框 -->
    <el-dialog v-model="showProtocolDialog" title="切换充电协议" :width="420" class="glass-dialog">
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
        <button class="btn-glass btn-glass-sm" @click="showProtocolDialog = false">取消</button>
        <button class="btn-glass btn-glass-primary btn-glass-sm" :disabled="!selectedProtocolId" @click="handleUpdateProtocol">切换到此协议</button>
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

const showSwitchDialog = ref(false)
const switchOptions = ref<any[]>([])
const targetStationId = ref<number | null>(null)
const showEnergyDialog = ref(false)
const newEnergyValue = ref(0)
const minEnergy = computed(() => Math.max(0.1, (session.value?.chargedEnergyKwh || 0) + 0.1))
const maxEnergy = ref(200)
const showProtocolDialog = ref(false)
const protocolOptions = ref<any[]>([])
const selectedProtocolId = ref<number | null>(null)
const waitingProtocols = ref<any[]>([])
const selectedWaitingProtocol = ref<number | null>(null)
const confirmLoading = ref(false)
const protocolsLoaded = ref(false)

const clampWidth = computed(() => {
  if (typeof window === 'undefined') return 100
  return Math.max(72, Math.min(120, Math.round(window.innerWidth / 8)))
})

async function loadWaitingProtocols() {
  if (protocolsLoaded.value) return
  protocolsLoaded.value = true
  try {
    const res = await getProtocolOptionsApi(Number(route.params.id))
    const body = res.data as any
    waitingProtocols.value = body.data?.options || []
    if (waitingProtocols.value.length > 0) selectedWaitingProtocol.value = waitingProtocols.value[0].id
  } catch { waitingProtocols.value = [] }
}

watch(() => session.value?.advanceReady, (val) => { if (val === false) protocolsLoaded.value = false })

async function handleConfirmCharging() {
  if (!selectedWaitingProtocol.value) { ElMessage.warning('请选择充电协议'); return }
  confirmLoading.value = true
  try {
    await confirmChargingApi(Number(route.params.id), { action: 'confirm', protocolId: selectedWaitingProtocol.value })
    ElMessage.success('⚡ 开始充电'); fetchSession()
  } catch (err: any) { ElMessage.error(err?.response?.data?.message || '确认失败') }
  finally { confirmLoading.value = false }
}

async function handleRejectConfirm() {
  try {
    await ElMessageBox.confirm('确定退出？将根据当前状态收取相应费用', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const res = await confirmChargingApi(Number(route.params.id), { action: 'reject' })
    ElMessage.success((res.data as any).message || '已退出'); stopPolling(); fetchSession()
  } catch (err: any) {
    if (err?.code !== 'cancel') ElMessage.error(err?.response?.data?.message || '操作失败')
  }
}

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

async function handleCancel() {
  try {
    await ElMessageBox.confirm(session.value.status === 'queued' ? '确定取消排队？免费取消' : '确定退出？将收取基础服务费', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    const res = await cancelSessionApi(Number(route.params.id))
    ElMessage.success((res.data as any).message || '已取消'); stopPolling(); fetchSession()
  } catch (err: any) { if (err?.code !== 'cancel') ElMessage.error(err?.response?.data?.message || '取消失败') }
}

function openEnergyDialog() { newEnergyValue.value = session.value?.requestedEnergyKwh || 60; showEnergyDialog.value = true }

async function handleUpdateEnergy() {
  try {
    await updateEnergyApi(Number(route.params.id), newEnergyValue.value)
    ElMessage.success('目标电量已更新'); showEnergyDialog.value = false; fetchSession()
  } catch (err: any) { ElMessage.error(err?.response?.data?.message || '修改失败') }
}

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

async function handleStopCharging() {
  try {
    await ElMessageBox.confirm(`确定停止充电？已充电量 ${session.value?.chargedEnergyKwh} kWh，将按实际用量计费`, '停止充电', { confirmButtonText: '确定停止', cancelButtonText: '取消', type: 'warning' })
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
.session-progress {
  max-width: 640px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: clamp(12px, 1.5vw, 16px);
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-card {
  padding: clamp(20px, 3vw, 24px);
  text-align: center;
}

.queue-number {
  font-size: clamp(48px, 8vw, 72px);
  font-weight: 700;
  color: var(--color-primary);
  font-family: 'JetBrains Mono', monospace;
  line-height: 1;
}

.queue-label {
  font-size: clamp(14px, 1.8vw, 16px);
  color: var(--text-tertiary);
  margin: 4px 0 12px;
}

.queue-info p { margin: 4px 0; }
.info-text { font-size: clamp(13px, 1.2vw, 14px); color: var(--text-tertiary); }

.waiting-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: clamp(24px, 4vw, 40px) clamp(16px, 2.5vw, 24px);
}

.waiting-icon { font-size: clamp(32px, 5vw, 40px); }
.waiting-title { font-size: clamp(16px, 2vw, 18px); font-weight: 600; color: var(--text-primary); text-align: center; }
.fee-preview { font-size: 13px; color: var(--text-secondary); }

.charging-info-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: clamp(12px, 1.5vw, 16px);
}

@media (max-width: 520px) {
  .charging-info-row {
    grid-template-columns: 1fr;
  }
}

.charging-main {
  display: flex;
  align-items: center;
  gap: clamp(12px, 2vw, 20px);
  padding: clamp(16px, 2.5vw, 24px);
}

.charging-right {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.charging-energy {
  font-size: clamp(16px, 2vw, 20px);
  font-weight: 600;
  color: var(--color-success);
  font-family: 'JetBrains Mono', monospace;
  word-break: break-all;
}

.energy-val { font-size: 1.2em; }
.energy-sep { color: var(--text-tertiary); margin: 0 2px; }
.energy-target { color: var(--text-tertiary); font-weight: 400; font-size: 0.85em; }

.charging-duration { font-size: 13px; color: var(--text-tertiary); }

.fee-card { padding: clamp(16px, 2.5vw, 24px); }
.fee-header { font-size: 15px; font-weight: 600; margin-bottom: 12px; color: var(--text-primary); }
.fee-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 14px; color: var(--text-secondary); }
.fee-value { font-family: 'JetBrains Mono', monospace; color: var(--text-primary); font-size: clamp(13px, 1.2vw, 14px); }
.fee-row.total { font-size: clamp(14px, 1.5vw, 16px); font-weight: 600; margin-top: 4px; }
.fee-total { color: var(--color-danger); font-size: clamp(17px, 2vw, 20px); font-weight: 700; font-family: 'JetBrains Mono', monospace; }

.action-row { display: flex; justify-content: center; gap: clamp(8px, 1.2vw, 12px); flex-wrap: wrap; }
.charging-actions { display: flex; gap: 8px; }

.result-card { text-align: center; padding: clamp(32px, 6vw, 48px) clamp(16px, 2vw, 24px); }
.result-icon { font-size: clamp(48px, 8vw, 64px); margin-bottom: 16px; }
.result-card h3 { font-size: clamp(20px, 3vw, 24px); font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.result-text { color: var(--text-secondary); font-size: 14px; }

/* 换队 */
.switch-options { display: flex; flex-direction: column; gap: 12px; width: 100%; }
.switch-option { width: 100%; padding: 12px 16px; height: auto !important; border-radius: 8px; margin-right: 0; }
.switch-option :deep(.el-radio__label) { width: 100%; }
.option-content { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.option-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px; }
.option-header strong { font-size: clamp(14px, 1.3vw, 15px); color: var(--text-primary); }
.option-wait { font-size: 12px; }
.option-metrics { display: flex; gap: clamp(8px, 1vw, 12px); font-size: clamp(11px, 1vw, 12px); color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; flex-wrap: wrap; }
.option-protocols { display: flex; flex-wrap: wrap; gap: 4px; }
.no-options { text-align: center; padding: 24px; color: var(--text-tertiary); }
.form-tip { font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }

/* 协议 */
.dialog-hint { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }
.protocol-radios { display: flex; flex-direction: column; gap: 8px; width: 100%; }
.protocol-radio { width: 100%; margin-right: 0; padding: 10px 12px; border-radius: 8px; }
.protocol-radio-content { display: flex; justify-content: space-between; align-items: center; }
.protocol-radio-content strong { font-size: clamp(13px, 1.2vw, 15px); }
.protocol-power { font-size: 13px; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; }

.protocol-section { width: 100%; margin-top: 12px; }
.section-label { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; text-align: left; }
.waiting-protocols { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.waiting-proto-option { width: 100%; margin-right: 0; padding: 8px 12px; border-radius: 6px; }
.proto-option-content { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.proto-option-content strong { font-size: clamp(13px, 1.2vw, 14px); color: var(--text-primary); }

.loading-wrapper { padding: 48px; }
</style>
