<template>
  <div class="queue-manage">
    <div class="page-header">
      <div>
        <h2>📋 队列管理</h2>
        <p class="page-desc">查看和调整各充电桩三区队列</p>
      </div>
      <button class="btn-glass btn-glass-primary" @click="fetchQueues" :disabled="loading">
        {{ loading ? '⟳ 刷新中...' : '⟳ 刷新队列' }}
      </button>
    </div>

    <div v-if="loading" class="loading-wrapper">
      <el-skeleton :rows="5" animated />
    </div>

    <template v-else-if="stations.length">
      <div v-for="s in stations" :key="s.stationId" class="glass-card station-card">
        <div class="station-header">
          <div class="station-title">
            <strong>{{ s.stationName }}</strong>
            <el-tag :type="s.status === 'running' ? 'success' : 'danger'" size="small" effect="light">
              {{ s.status === 'running' ? '运行中' : s.status === 'stopping' ? '停止中' : '已停止' }}
            </el-tag>
          </div>
          <div class="station-capacity">
            <span class="glass-badge queue-color">🚶 {{ s.capacity.queue.current }}/{{ s.capacity.queue.max }}</span>
            <span class="glass-badge waiting-color">⏳ {{ s.capacity.waiting.current }}/{{ s.capacity.waiting.max }}</span>
            <span class="glass-badge charging-color">⚡ {{ s.capacity.charging.current }}/{{ s.capacity.charging.max }}</span>
          </div>
        </div>

        <div class="zone-grid">
          <!-- 排队区 -->
          <div class="zone-column">
            <div class="zone-header" style="border-left-color:#3B82F6;">🚶 排队区</div>
            <div class="zone-list glass-card-strong" @dragover.prevent @drop="onDrop($event, s.stationId, 'queue')">
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
                  <span>{{ item.requestedEnergyKwh }} kWh</span>
                  <span class="item-status" v-if="item.advanceReady">就绪</span>
                </div>
                <div class="item-actions">
                  <button class="btn-glass btn-glass-sm" style="padding:2px 8px;font-size:11px;min-height:28px;" @click.stop="openMoveDialog(item, s.stationId, 'queue')">移动</button>
                  <button class="btn-glass btn-glass-sm" style="padding:2px 8px;font-size:11px;min-height:28px;" @click.stop="openReorderDialog(item, s.stationId, 'queue', idx)">重排</button>
                </div>
              </div>
              <div v-if="!s.queueList.length" class="zone-empty">空闲</div>
            </div>
          </div>

          <!-- 等待区 -->
          <div class="zone-column">
            <div class="zone-header" style="border-left-color:#F59E0B;">⏳ 等待区</div>
            <div class="zone-list glass-card-strong" @dragover.prevent @drop="onDrop($event, s.stationId, 'waiting')">
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
                  <span>{{ item.requestedEnergyKwh }} kWh</span>
                  <span class="item-status" v-if="item.advanceReady">就绪</span>
                </div>
                <div class="item-actions">
                  <button class="btn-glass btn-glass-sm" style="padding:2px 8px;font-size:11px;min-height:28px;" @click.stop="openMoveDialog(item, s.stationId, 'waiting')">移动</button>
                  <button class="btn-glass btn-glass-sm" style="padding:2px 8px;font-size:11px;min-height:28px;" @click.stop="openReorderDialog(item, s.stationId, 'waiting', idx)">重排</button>
                </div>
              </div>
              <div v-if="!s.waitingList.length" class="zone-empty">空闲</div>
            </div>
          </div>

          <!-- 充电区 -->
          <div class="zone-column">
            <div class="zone-header" style="border-left-color:#22C55E;">⚡ 充电区</div>
            <div class="zone-list glass-card-strong">
              <div v-for="item in s.chargingList" :key="item.sessionId" class="queue-item charging-item">
                <div class="item-header">
                  <span class="item-plate">{{ item.licensePlate }}</span>
                </div>
                <div class="item-body">
                  <el-progress :percentage="item.progress" :width="36" type="circle" :stroke-width="4" color="#22C55E" />
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
      </div>
    </template>

    <EmptyState v-else icon="Warning" description="暂无充电桩数据" />

    <!-- 重排对话框 -->
    <el-dialog v-model="showReorder" title="修改队列位置" :width="360" class="glass-dialog">
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
        <button class="btn-glass btn-glass-sm" @click="showReorder = false">取消</button>
        <button class="btn-glass btn-glass-primary btn-glass-sm" :disabled="!reorderNewPos" @click="handleReorder">确认重排</button>
      </template>
    </el-dialog>

    <!-- 移动对话框 -->
    <el-dialog v-model="showMove" title="移动到其他桩" :width="420" class="glass-dialog">
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
        <button class="btn-glass btn-glass-sm" @click="showMove = false">取消</button>
        <button class="btn-glass btn-glass-primary btn-glass-sm" :disabled="!moveTargetStationId" @click="handleMove">
          确认移动
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdminQueuesApi, reorderQueueApi, moveSessionApi } from '@/api/admin/queue'
import EmptyState from '@/components/EmptyState.vue'

const loading = ref(true)
const stations = ref<any[]>([])

let dragItem: any = null
let dragFromStationId: number | null = null
let dragFromZone: string | null = null

const showReorder = ref(false)
const reorderTarget = ref<any>(null)
const reorderStationId = ref(0)
const reorderZone = ref('queue')
const reorderNewPos = ref(1)
const reorderMaxPos = ref(1)

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
  if (dragFromStationId === stationId && dragFromZone === zone) return
  try {
    await moveSessionApi({
      sessionId: dragItem.sessionId,
      targetStationId: stationId,
      targetZone: zone,
    })
    ElMessage.success('已移动到目标桩')
    fetchQueues()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '移动失败')
  }
}

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
      targetZone: 'queue',
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

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
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

.loading-wrapper { padding: 48px; }

.station-card { padding: 20px; margin-bottom: 20px; }

.station-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.station-title { display: flex; align-items: center; gap: 8px; }
.station-title strong { font-size: 16px; color: var(--text-primary); }
.station-capacity { display: flex; gap: 8px; flex-wrap: wrap; }

.queue-color { border-left-color: #3B82F6; }
.waiting-color { border-left-color: #F59E0B; }
.charging-color { border-left-color: #22C55E; }

.zone-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.zone-column { min-width: 0; }
.zone-header { font-size: 14px; font-weight: 600; padding: 10px 12px; border-left: 3px solid; margin-bottom: 8px; color: var(--text-primary); }
.zone-list { border-radius: 8px; padding: 8px; min-height: 80px; }

.queue-item { padding: 10px 12px; margin-bottom: 6px; cursor: grab; border-radius: 8px; transition: all 0.2s ease; background: var(--bg-glass); border: 1px solid var(--border-light); }
.queue-item:hover { border-color: var(--border-hover); }
.queue-item:active { cursor: grabbing; }
.item-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.item-pos { width: 22px; height: 22px; border-radius: 50%; background: var(--color-primary); color: #FFF; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; font-family: 'JetBrains Mono', monospace; }
.item-plate { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.item-body { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--text-tertiary); }
.item-status { background: var(--color-primary-bg); color: var(--color-primary); padding: 1px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.item-actions { margin-top: 6px; display: flex; gap: 4px; }
.charging-item .item-body { gap: 8px; }
.charging-info { display: flex; flex-direction: column; font-size: 11px; color: var(--text-tertiary); }
.zone-empty { text-align: center; color: var(--text-tertiary); font-size: 13px; padding: 24px 0; }
</style>
