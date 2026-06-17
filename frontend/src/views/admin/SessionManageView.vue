<template>
  <div class="session-manage">
    <div class="page-header">
      <div>
        <h2>📋 会话管理</h2>
        <p class="page-desc">查看和管理所有充电会话</p>
      </div>
    </div>

    <div class="glass-card filter-card">
      <el-form :inline="true" size="small">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width:120px" @change="fetchList(1)">
            <el-option label="排队中" value="queued" />
            <el-option label="等待中" value="waiting" />
            <el-option label="充电中" value="charging" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="充电桩">
          <el-select v-model="filters.stationId" placeholder="全部" clearable style="width:140px" @change="fetchList(1)">
            <el-option v-for="s in stationOptions" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <button class="btn-glass btn-glass-sm" @click="resetFilters">🔄 重置</button>
          <button class="btn-glass btn-glass-sm" @click="fetchList()" :disabled="loading">
            {{ loading ? '⟳' : '⟳ 刷新' }}
          </button>
        </el-form-item>
      </el-form>
    </div>

    <div class="glass-card table-card">
      <div class="table-scroll">
        <el-table :data="sessions" v-loading="loading" stripe style="width:100%" @row-click="openDetail">
        <el-table-column label="ID" width="60">
          <template #default="{ row }">{{ row.sessionId }}</template>
        </el-table-column>
        <el-table-column label="车牌号" width="110">
          <template #default="{ row }">{{ row.user?.licensePlate }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="充电桩" min-width="130">
          <template #default="{ row }">{{ row.station?.name }}</template>
        </el-table-column>
        <el-table-column label="目标电量" width="100">
          <template #default="{ row }">{{ row.requestedEnergyKwh }} kWh</template>
        </el-table-column>
        <el-table-column label="已充电量" width="100">
          <template #default="{ row }">{{ row.chargedEnergyKwh?.toFixed(2) }} kWh</template>
        </el-table-column>
        <el-table-column label="进度" width="80">
          <template #default="{ row }">{{ row.progress ?? 0 }}%</template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="150">
          <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
      </el-table>

      </div>
      <div class="pagination" v-if="total > pageSize">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
          layout="prev, pager, next" @current-change="fetchList" />
      </div>
    </div>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetail" title="会话详情" :width="500" class="glass-dialog">
      <template v-if="detail">
        <div class="detail-row"><label>会话 ID</label><span>{{ detail.id }}</span></div>
        <div class="detail-row"><label>用户</label><span>{{ detail.user?.licensePlate }}</span></div>
        <div class="detail-row"><label>充电桩</label><span>{{ detail.station?.name }}</span></div>
        <div class="detail-row"><label>状态</label><span>{{ statusLabel(detail.status) }}</span></div>
        <div class="detail-row"><label>区域</label><span>{{ detail.zone || '-' }}</span></div>
        <div class="detail-row"><label>协议</label><span>{{ detail.protocol?.name || '-' }}</span></div>
        <div class="detail-row"><label>目标电量</label><span>{{ detail.requestedEnergyKwh }} kWh</span></div>
        <div class="detail-row"><label>已充电量</label><span>{{ detail.chargedEnergyKwh?.toFixed(2) }} kWh</span></div>
        <div class="detail-row"><label>进度</label><span>{{ detail.progress }}%</span></div>
        <div class="detail-row"><label>排队位置</label><span>{{ detail.queuePosition ?? '-' }}</span></div>
        <div class="detail-row"><label>创建时间</label><span>{{ formatTime(detail.createdAt) }}</span></div>
        <div class="detail-row" v-if="detail.enteredWaitingAt"><label>进入等待区</label><span>{{ formatTime(detail.enteredWaitingAt) }}</span></div>
        <div class="detail-row" v-if="detail.startedChargingAt"><label>开始充电</label><span>{{ formatTime(detail.startedChargingAt) }}</span></div>
        <div class="detail-row" v-if="detail.completedAt"><label>完成时间</label><span>{{ formatTime(detail.completedAt) }}</span></div>
      </template>
      <template #footer>
        <button class="btn-glass btn-glass-sm" @click="showDetail = false">关闭</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdminSessionsApi, getAdminSessionDetailApi } from '@/api/admin/session'
import { getAdminStationsApi } from '@/api/admin/station'
import { formatTime } from '@/utils/format'

const loading = ref(false)
const sessions = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const stationOptions = ref<any[]>([])
const showDetail = ref(false)
const detail = ref<any>(null)

const filters = ref<{ status?: string; stationId?: number }>({})

function statusType(s: string) {
  const map: Record<string, string> = { queued: 'primary', waiting: 'warning', charging: 'success', completed: 'info', cancelled: 'info' }
  return map[s] || 'info'
}
function statusLabel(s: string) {
  const map: Record<string, string> = { queued: '排队中', waiting: '等待中', charging: '充电中', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}

async function fetchList(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const params: any = { page: page.value, pageSize: pageSize.value }
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.stationId) params.stationId = filters.value.stationId
    const res = await getAdminSessionsApi(params)
    const data = (res.data as any).data
    sessions.value = data.list || []
    total.value = data.total
    page.value = data.page
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '加载失败')
  } finally { loading.value = false }
}

function resetFilters() {
  filters.value = {}
  fetchList(1)
}

async function openDetail(row: any) {
  try {
    const res = await getAdminSessionDetailApi(row.sessionId)
    detail.value = (res.data as any).data
    showDetail.value = true
  } catch { /* ignore */ }
}

async function fetchStations() {
  try {
    const res = await getAdminStationsApi()
    stationOptions.value = (res.data as any).data?.stations || []
  } catch { stationOptions.value = [] }
}

onMounted(() => { fetchList(1); fetchStations() })
</script>

<style scoped>
.session-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

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

.filter-card {
  padding: 16px;
}

.filter-card :deep(.el-form) {
  margin-bottom: -18px;
}

.table-card {
  padding: 4px;
  overflow: hidden;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding: 12px 0;
}

.detail-row {
  display: flex;
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px solid var(--border-light);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row label {
  width: 100px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.detail-row span {
  color: var(--text-primary);
}
</style>
