<template>
  <div class="bill-manage">
    <h2>账单管理</h2>

    <el-card shadow="never" class="filter-card">
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
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" :icon="Refresh" @click="fetchList()" :loading="loading" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="bills" v-loading="loading" stripe style="width:100%" @row-click="openDetail">
        <el-table-column prop="billId" label="账单ID" width="70" />
        <el-table-column prop="licensePlate" label="车牌号" width="100" />
        <el-table-column prop="stationName" label="充电桩" min-width="120" />
        <el-table-column prop="totalEnergyKwh" label="电量" width="80">
          <template #default="{ row }">{{ row.totalEnergyKwh }} kWh</template>
        </el-table-column>
        <el-table-column prop="totalFee" label="总金额" width="90">
          <template #default="{ row }">¥{{ row.totalFee?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="支付状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.paymentStatus === 'paid' ? 'success' : 'warning'" size="small" effect="light">
              {{ row.paymentStatus === 'paid' ? '已支付' : '未支付' }}
            </el-tag>
          </template>
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
    <el-dialog v-model="showDetail" title="账单详情" :width="520">
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
            {{ detail.paymentStatus === 'paid' ? '已支付' : '未支付' }}
          </el-tag>
        </div>
        <div class="detail-row" v-if="detail.transactionId"><label>交易流水</label><span class="txn">{{ detail.transactionId }}</span></div>
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
.bill-manage h2 { font-size: 22px; font-weight: 600; margin-bottom: 16px; color: #1E293B; }
.filter-card { border-radius: 10px; margin-bottom: 16px; }
.pagination { display: flex; justify-content: center; margin-top: 16px; }
.detail-row { display: flex; padding: 6px 0; font-size: 14px; border-bottom: 1px solid #F1F5F9; }
.detail-row label { width: 100px; color: #94A3B8; flex-shrink: 0; }
.detail-row span { color: #1E293B; }
.detail-row .fee { color: #475569; font-family: 'JetBrains Mono', monospace; }
.detail-row.total { font-weight: 600; }
.detail-row .total-fee { color: #EA580C; font-size: 16px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.txn { color: #2563EB; font-size: 12px; font-family: 'JetBrains Mono', monospace; }
</style>
