<template>
  <div class="bill-manage">
    <div class="page-header">
      <div>
        <h2>📋 账单管理</h2>
        <p class="page-desc">查看和管理所有充电账单</p>
      </div>
    </div>

    <div class="glass-card filter-card">
      <el-form :inline="true" size="small">
        <el-form-item label="支付状态">
          <el-select v-model="filters.paymentStatus" placeholder="全部" clearable style="width:120px" @change="fetchList(1)">
            <el-option label="未支付" value="unpaid" />
            <el-option label="已支付" value="paid" />
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
        <el-table :data="bills" v-loading="loading" stripe style="width:100%" @row-click="openDetail">
        <el-table-column prop="billId" label="账单ID" width="70" />
        <el-table-column label="车牌号" width="110">
          <template #default="{ row }">{{ row.user?.licensePlate }}</template>
        </el-table-column>
        <el-table-column label="充电桩" min-width="130">
          <template #default="{ row }">{{ row.station?.name }}</template>
        </el-table-column>
        <el-table-column label="电量" width="80">
          <template #default="{ row }">{{ row.chargedEnergyKwh }} kWh</template>
        </el-table-column>
        <el-table-column prop="totalFee" label="总金额" width="100">
          <template #default="{ row }">¥{{ row.totalFee?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="支付状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.paymentStatus === 'paid' ? 'success' : 'warning'" size="small" effect="light">
              {{ row.paymentStatus === 'paid' ? '✅ 已支付' : '⏳ 未支付' }}
            </el-tag>
          </template>
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
    <el-dialog v-model="showDetail" title="账单详情" :width="520" class="glass-dialog">
      <template v-if="detail">
        <div class="detail-row"><label>账单 ID</label><span>{{ detail.id }}</span></div>
        <div class="detail-row"><label>会话 ID</label><span>{{ detail.sessionId }}</span></div>
        <div class="detail-row"><label>用户</label><span>{{ detail.user?.licensePlate }}</span></div>
        <div class="detail-row"><label>充电桩</label><span>{{ detail.station?.name }}</span></div>
        <div class="detail-row"><label>充电时长</label><span>{{ detail.chargingDuration }}</span></div>
        <div class="detail-row"><label>充电量</label><span>{{ detail.chargedEnergyKwh }} kWh</span></div>
        <div class="detail-row"><label>电费</label><span class="fee">¥{{ detail.electricityFee?.toFixed(2) }}</span></div>
        <div class="detail-row"><label>服务费</label><span class="fee">¥{{ detail.totalServiceFee?.toFixed(2) }}</span></div>
        <div class="detail-row total"><label>总费用</label><span class="total-fee">¥{{ detail.totalFee?.toFixed(2) }}</span></div>
        <div class="detail-row"><label>支付状态</label>
          <el-tag :type="detail.paymentStatus === 'paid' ? 'success' : 'warning'" size="small">
            {{ detail.paymentStatus === 'paid' ? '✅ 已支付' : '⏳ 未支付' }}
          </el-tag>
        </div>
        <div class="detail-row" v-if="detail.transactionId"><label>交易流水</label><span class="txn">{{ detail.transactionId }}</span></div>
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
import { getAdminBillsApi, getAdminBillDetailApi } from '@/api/admin/bill'
import { getAdminStationsApi } from '@/api/admin/station'
import { formatTime } from '@/utils/format'

const loading = ref(false)
const bills = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const stationOptions = ref<any[]>([])
const showDetail = ref(false)
const detail = ref<any>(null)

const filters = ref<{ paymentStatus?: string; stationId?: number }>({})

async function fetchList(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const params: any = { page: page.value, pageSize: pageSize.value }
    if (filters.value.paymentStatus) params.paymentStatus = filters.value.paymentStatus
    if (filters.value.stationId) params.stationId = filters.value.stationId
    const res = await getAdminBillsApi(params)
    const data = (res.data as any).data
    bills.value = data.list || []
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
    const res = await getAdminBillDetailApi(row.billId)
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
.bill-manage {
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

.detail-row .fee {
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', monospace;
}

.detail-row.total {
  font-weight: 600;
}

.detail-row .total-fee {
  color: var(--color-danger);
  font-size: 16px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.txn {
  color: var(--color-primary);
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
}
</style>
