<template>
  <div class="session-manage">
    <h2>会话管理</h2>

    <el-card shadow="never" class="filter-card">
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
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" :icon="Refresh" @click="fetchList()" :loading="loading" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="sessions" v-loading="loading" stripe style="width:100%" @row-click="openDetail">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="licensePlate" label="车牌号" width="100" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="stationName" label="充电桩" min-width="120" />
        <el-table-column prop="requestedEnergyKwh" label="目标电量" width="90">
          <template #default="{ row }">{{ row.requestedEnergyKwh }} kWh</template>
        </el-table-column>
        <el-table-column prop="chargedEnergyKwh" label="已充电量" width="90">
          <template #default="{ row }">{{ row.chargedEnergyKwh?.toFixed(2) }} kWh</template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="140">
          <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination" v-if="total > pageSize">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
          layout="prev, pager, next" @current-change="fetchList" />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetail" title="会话详情" :width="500">
      <template v-if="detail">
        <div class="detail-row"><label>会话 ID</label><span>{{ detail.id }}</span></div>
        <div class="detail-row"><label>用户</label><span>{{ detail.licensePlate }} ({{ detail.userName }})</span></div>
        <div class="detail-row"><label>充电桩</label><span>{{ detail.stationName }}</span></div>
        <div class="detail-row"><label>状态</label><span>{{ statusLabel(detail.status) }}</span></div>
        <div class="detail-row"><label>区域</label><span>{{ detail.zone || '-' }}</span></div>
        <div class="detail-row"><label>协议</label><span>{{ detail.protocol?.name || '-' }}</span></div>
        <div class="detail-row"><label>目标电量</label><span>{{ detail.requestedEnergyKwh }} kWh</span></div>
        <div class="detail-row"><label>已充电量</label><span>{{ detail.chargedEnergyKwh?.toFixed(2) }} kWh</span></div>
        <div class="detail-row"><label>排队位置</label><span>{{ detail.queuePosition ?? '-' }}</span></div>
        <div class="detail-row"><label>创建时间</label><span>{{ formatTime(detail.createdAt) }}</span></div>
        <div class="detail-row" v-if="detail.enteredWaitingAt"><label>进入等待区</label><span>{{ formatTime(detail.enteredWaitingAt) }}</span></div>
        <div class="detail-row" v-if="detail.startedChargingAt"><label>开始充电</label><span>{{ formatTime(detail.startedChargingAt) }}</span></div>
        <div class="detail-row" v-if="detail.completedAt"><label>完成时间</label><span>{{ formatTime(detail.completedAt) }}</span></div>
      </template>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
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
    const res = await getAdminSessionDetailApi(row.id)
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
.session-manage h2 { font-size: 22px; font-weight: 600; margin-bottom: 16px; color: #1E293B; }
.filter-card { border-radius: 10px; margin-bottom: 16px; }
.pagination { display: flex; justify-content: center; margin-top: 16px; }
.detail-row { display: flex; padding: 6px 0; font-size: 14px; border-bottom: 1px solid #F1F5F9; }
.detail-row label { width: 100px; color: #94A3B8; flex-shrink: 0; }
.detail-row span { color: #1E293B; }
</style>
