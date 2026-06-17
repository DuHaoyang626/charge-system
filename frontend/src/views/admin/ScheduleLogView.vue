<template>
  <div class="schedule-log">
    <div class="page-header">
      <div>
        <h2>📋 调度日志</h2>
        <p class="page-desc">查看系统调度操作记录</p>
      </div>
      <button class="btn-glass btn-glass-primary" @click="() => fetchLogs()" :disabled="loading">
        {{ loading ? '⟳ 刷新中...' : '⟳ 刷新日志' }}
      </button>
    </div>

    <div class="glass-card filter-card">
      <el-form :inline="true" size="small">
        <el-form-item label="会话 ID">
          <el-input-number v-model="searchSessionId" :min="1" :max="999999" style="width:130px"
            placeholder="全部" controls-position="right" @change="fetchLogs(1)" />
        </el-form-item>
        <el-form-item>
          <button class="btn-glass btn-glass-sm" @click="searchSessionId=undefined;fetchLogs(1)">🔄 重置</button>
        </el-form-item>
      </el-form>
    </div>

    <div class="glass-card table-card">
      <div class="table-scroll">
        <el-table :data="logs" v-loading="loading" stripe style="width:100%" :default-sort="{ prop: 'createdAt', order: 'descending' }">
        <el-table-column prop="id" label="ID" width="60" sortable />
        <el-table-column prop="sessionId" label="会话ID" width="80" />
        <el-table-column prop="licensePlate" label="车牌号" width="110" />
        <el-table-column label="从" width="110">
          <template #default="{ row }">{{ row.fromStation || '-' }}<br><small>{{ row.fromZone || '' }}</small></template>
        </el-table-column>
        <el-table-column label="到" width="110">
          <template #default="{ row }">{{ row.toStation || '-' }}<br><small>{{ row.toZone || '' }}</small></template>
        </el-table-column>
        <el-table-column label="触发方式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.triggeredBy === 'system' ? 'primary' : row.triggeredBy === 'admin' ? 'warning' : 'success'" size="small" effect="light">
              {{ row.triggeredBy === 'system' ? '系统' : row.triggeredBy === 'admin' ? '管理员' : '用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="时间" width="160" sortable>
          <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
      </el-table>

      </div>
      <div class="pagination" v-if="total > pageSize">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
          layout="prev, pager, next" @current-change="fetchLogs" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api/request'
import { formatTime } from '@/utils/format'

const loading = ref(false)
const logs = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchSessionId = ref<number | undefined>()

async function fetchLogs(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const params: any = { page: page.value, pageSize: pageSize.value }
    if (searchSessionId.value) params.sessionId = searchSessionId.value
    const res = await api.get('/admin/queues/logs', { params })
    const data = (res.data as any).data
    logs.value = data.list || []
    total.value = data.total
    page.value = data.page
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '加载失败')
  } finally { loading.value = false }
}

onMounted(() => fetchLogs(1))
</script>

<style scoped>
.schedule-log {
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
  margin: 0;
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

small { color: var(--text-tertiary); font-size: 11px; }
</style>
