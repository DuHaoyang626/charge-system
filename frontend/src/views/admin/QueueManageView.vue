<template>
  <div class="queue-manage">
    <div class="page-header">
      <h2>队列管理</h2>
      <el-button type="primary" @click="fetchQueues" :loading="loading" :icon="Refresh">
        刷新
      </el-button>
    </div>

    <div v-if="loading" class="loading-wrapper">
      <el-skeleton :rows="5" animated />
    </div>

    <template v-else-if="stations.length">
      <el-card v-for="s in stations" :key="s.stationId" shadow="never" class="station-card">
        <!-- 桩标题 -->
        <template #header>
          <div class="station-header">
            <div class="station-title">
              <strong>{{ s.stationName }}</strong>
              <el-tag :type="s.status === 'running' ? 'success' : 'danger'" size="small" effect="light">
                {{ s.status === 'running' ? '运行中' : s.status === 'stopping' ? '停止中' : '已停止' }}
              </el-tag>
            </div>
            <div class="station-capacity">
              <span class="cap-item queue-color">排队 {{ s.capacity.queue.current }}/{{ s.capacity.queue.max }}</span>
              <span class="cap-item waiting-color">等待 {{ s.capacity.waiting.current }}/{{ s.capacity.waiting.max }}</span>
              <span class="cap-item charging-color">充电 {{ s.capacity.charging.current }}/{{ s.capacity.charging.max }}</span>
            </div>
          </div>
        </template>

        <!-- 三区 -->
        <div class="zone-grid">
          <!-- 排队区 -->
          <div class="zone-column">
            <div class="zone-header queue-bg">🚶 排队区</div>
            <div class="zone-list" @dragover.prevent @drop="onDrop($event, s.stationId, 'queue')">
              <div v-for="(item, idx) in s.queueList" :key="item.sessionId"
                class="queue-item"
                draggable="true"
                @dragstart="onDragStart($event, item, s.stationId, 'queue')"
                @dragend="onDragEnd">
                <div class="item-header">
                  <span class="item-pos">{{ item.position }}</span>
                  <span class="item-plate">{{ item.licensePlate }}</span>
                </div>
                <div class="item-body">
                  <span class="item-energy">{{ item.requestedEnergyKwh }} kWh</span>
                  <span class="item-status" v-if="item.advanceReady">就绪</span>
                </div>
                <div class="item-actions">
                  <el-button text size="small" @click.stop="openMoveDialog(item, s.stationId, 'queue')">移动</el-button>
                  <el-button text size="small" @click.stop="openReorderDialog(item, s.stationId, 'queue', idx)">重排</el-button>
                </div>
              </div>
              <div v-if="!s.queueList.length" class="zone-empty">空闲</div>
            </div>
          </div>

          <!-- 等待区 -->
          <div class="zone-column">
            <div class="zone-header waiting-bg">⏳ 等待区</div>
            <div class="zone-list" @dragover.prevent @drop="onDrop($event, s.stationId, 'waiting')">
              <div v-for="(item, idx) in s.waitingList" :key="item.sessionId"
                class="queue-item"
                draggable="true"
                @dragstart="onDragStart($event, item, s.stationId, 'waiting')"
                @dragend="onDragEnd">
                <div class="item-header">
                  <span class="item-pos">{{ item.position }}</span>
                  <span class="item-plate">{{ item.licensePlate }}</span>
                </div>
                <div class="item-body">
                  <span class="item-energy">{{ item.requestedEnergyKwh }} kWh</span>
                  <span class="item-status" v-if="item.advanceReady">就绪</span>
                </div>
                <div class="item-actions">
                  <el-button text size="small" @click.stop="openMoveDialog(item, s.stationId, 'waiting')">移动</el-button>
                  <el-button text size="small" @click.stop="openReorderDialog(item, s.stationId, 'waiting', idx)">重排</el-button>
                </div>
              </div>
              <div v-if="!s.waitingList.length" class="zone-empty">空闲</div>
            </div>
          </div>

          <!-- 充电区 -->
          <div class="zone-column">
            <div class="zone-header charging-bg">⚡ 充电区</div>
            <div class="zone-list">
              <div v-for="item in s.chargingList" :key="item.sessionId" class="queue-item charging-item">
                <div class="item-header">
                  <span class="item-plate">{{ item.licensePlate }}</span>
                </div>
                <div class="item-body">
                  <el-progress :percentage="item.progress" :width="36" type="circle" :stroke-width="4" color="#16A34A" />
                  <div class="charging-info">
                    <span>{{ item.chargedEnergyKwh }}/{{ item.targetEnergyKwh }} kWh</span>
                    <span v-if="item.protocol">{{ item.protocol.name }}</span>
                  </div>
                </div>
              </div>
              <div v-if="!s.chargingList.length" class="zone-empty">空闲</div>
            </div>
          </div>
        </div>

      </el-card>
    </template>

    <EmptyState v-else icon="Warning" description="暂无充电桩数据" />

    <!-- 重排对话框 -->
    <el-dialog v-model="showReorder" title="修改队列位置" :width="360">
      <el-form label-position="top">
        <el-form-item label="当前车辆">
          <el-tag>{{ reorderTarget?.licensePlate }}</el-tag>
        </el-form-item>
        <el-form-item label="当前位置">
          <el-tag type="info">{{ reorderTarget?.currentPosition }}</el-tag>
        </el-form-item>
        <el-form-item label="新位置">
          <el-input-number v-model="reorderNewPos" :min="1" :max="reorderMaxPos" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReorder = false">取消</el-button>
        <el-button type="primary" :disabled="!reorderNewPos" @click="handleReorder">确认重排</el-button>
      </template>
    </el-dialog>

    <!-- 移动对话框 -->
    <el-dialog v-model="showMove" title="移动到其他桩" :width="420">
      <el-form label-position="top">
        <el-form-item label="当前车辆">
          <el-tag>{{ moveTarget?.licensePlate }}</el-tag>
        </el-form-item>
        <el-form-item label="当前桩">
          <el-tag type="info">{{ moveFromStationName }}</el-tag>
        </el-form-item>
        <el-form-item label="目标充电桩">
          <el-select v-model="moveTargetStationId" placeholder="请选择" style="width:100%">
            <el-option v-for="s in stationOptions" :key="s.stationId"
              :label="s.stationName" :value="s.stationId" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMove = false">取消</el-button>
        <el-button type="primary" :disabled="!moveTargetStationId" @click="handleMove">
          确认移动
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAdminQueuesApi, reorderQueueApi, moveSessionApi } from '@/api/admin/queue'
import EmptyState from '@/components/EmptyState.vue'

const loading = ref(true)
const stations = ref<any[]>([])

// 拖拽
let dragItem: any = null
let dragFromStationId: number | null = null
let dragFromZone: string | null = null

// 重排
const showReorder = ref(false)
const reorderTarget = ref<any>(null)
const reorderStationId = ref(0)
const reorderZone = ref('queue')
const reorderNewPos = ref(1)
const reorderMaxPos = ref(1)

// 移动
const showMove = ref(false)
const moveTarget = ref<any>(null)
const moveFromStationId = ref(0)
const moveFromStationName = ref('')
const moveTargetStationId = ref<number | null>(null)

async function fetchQueues() {
  loading.value = true
  try {
    const res = await getAdminQueuesApi()
    stations.value = (res.data as any).data.stations
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '加载队列失败')
  } finally { loading.value = false }
}

// ── 拖拽重排 ──
function onDragStart(e: DragEvent, item: any, stationId: number, zone: string) {
  dragItem = item
  dragFromStationId = stationId
  dragFromZone = zone
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(item.sessionId))
  }
}

function onDragEnd() {
  dragItem = null
  dragFromStationId = null
  dragFromZone = null
}

async function onDrop(e: DragEvent, stationId: number, zone: string) {
  if (!dragItem) return
  if (dragFromStationId === stationId && dragFromZone === zone) {
    // 同区重排
    return
  }
  // 跨桩移动
  try {
    await moveSessionApi({
      sessionId: dragItem.sessionId,
      targetStationId: stationId,
    })
    ElMessage.success('已移动到目标桩')
    fetchQueues()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '移动失败')
  }
}

// ── 重排 ──
function openReorderDialog(item: any, stationId: number, zone: string, idx: number) {
  reorderTarget.value = { ...item, currentPosition: item.position }
  reorderStationId.value = stationId
  reorderZone.value = zone
  const station = stations.value.find(s => s.stationId === stationId)
  const list = zone === 'queue' ? station?.queueList : station?.waitingList
  reorderMaxPos.value = list?.length || 1
  reorderNewPos.value = item.position
  showReorder.value = true
}

async function handleReorder() {
  try {
    await reorderQueueApi({
      stationId: reorderStationId.value,
      zone: reorderZone.value,
      sessionId: reorderTarget.value.sessionId,
      newPosition: reorderNewPos.value,
    })
    ElMessage.success('队列位置已更新')
    showReorder.value = false
    fetchQueues()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '重排失败')
  }
}

// ── 移动 ──
const stationOptions = computed(() =>
  stations.value.filter(s => s.stationId !== moveFromStationId.value)
)

function openMoveDialog(item: any, stationId: number, zone: string) {
  moveTarget.value = item
  moveFromStationId.value = stationId
  const station = stations.value.find(s => s.stationId === stationId)
  moveFromStationName.value = station?.stationName || ''
  moveTargetStationId.value = null
  showMove.value = true
}

async function handleMove() {
  if (!moveTargetStationId.value) return
  try {
    await moveSessionApi({
      sessionId: moveTarget.value.sessionId,
      targetStationId: moveTargetStationId.value,
    })
    ElMessage.success('车辆已移动到目标桩')
    showMove.value = false
    fetchQueues()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '移动失败')
  }
}

onMounted(fetchQueues)
</script>

<style scoped>
.queue-manage { max-width: 1200px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 22px; font-weight: 600; color: #1E293B; }
.loading-wrapper { padding: 48px; }

.station-card { border-radius: 12px; margin-bottom: 20px; }
.station-header { display: flex; justify-content: space-between; align-items: center; }
.station-title { display: flex; align-items: center; gap: 8px; }
.station-title strong { font-size: 16px; }
.station-capacity { display: flex; gap: 12px; font-size: 13px; font-family: 'JetBrains Mono', monospace; }
.cap-item { padding: 2px 8px; border-radius: 4px; }
.cap-item.queue-color { background: #EFF6FF; color: #2563EB; }
.cap-item.waiting-color { background: #FFF7ED; color: #D97706; }
.cap-item.charging-color { background: #F0FDF4; color: #16A34A; }

/* 三区网格 */
.zone-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.zone-column { min-width: 0; }
.zone-header { font-size: 14px; font-weight: 600; padding: 8px 12px; border-radius: 8px 8px 0 0; }
.queue-bg { background: #EFF6FF; color: #2563EB; }
.waiting-bg { background: #FFF7ED; color: #D97706; }
.charging-bg { background: #F0FDF4; color: #16A34A; }
.zone-list { border: 1px solid #E2E8F0; border-top: none; border-radius: 0 0 8px 8px; padding: 8px; min-height: 80px; }

/* 队列项 */
.queue-item { background: #FAFAFA; border: 1px solid #EBEBEB; border-radius: 8px; padding: 8px 10px; margin-bottom: 6px; cursor: grab; transition: box-shadow 0.2s; }
.queue-item:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
.queue-item:active { cursor: grabbing; }
.item-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.item-pos { width: 20px; height: 20px; border-radius: 50%; background: #2563EB; color: #FFF; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; font-family: 'JetBrains Mono', monospace; }
.item-plate { font-size: 13px; font-weight: 600; color: #1E293B; }
.item-body { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #64748B; }
.item-status { background: #DBEAFE; color: #2563EB; padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.item-actions { margin-top: 6px; display: flex; gap: 4px; }
.item-actions .el-button { padding: 0 4px; font-size: 12px; }

.charging-item .item-body { gap: 8px; }
.charging-info { display: flex; flex-direction: column; font-size: 11px; }

.zone-empty { text-align: center; color: #CBD5E1; font-size: 13px; padding: 24px 0; }

</style>
