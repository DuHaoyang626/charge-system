<template>
  <div class="bills-list">
    <div class="page-header">
      <h2>历史账单</h2>
      <el-tag type="info" effect="plain">共 {{ total }} 条</el-tag>
    </div>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" size="small">
        <el-form-item label="支付状态">
          <el-select v-model="filters.paymentStatus" placeholder="全部" clearable style="width:120px" @change="fetchBills(1)">
            <el-option label="未支付" value="unpaid" />
            <el-option label="已支付" value="paid" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="filters.startDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD"
            style="width:140px" @change="fetchBills(1)" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="filters.endDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD"
            style="width:140px" @change="fetchBills(1)" />
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-wrapper">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- 空状态 -->
    <EmptyState v-else-if="!bills.length" icon="Document" description="暂无账单记录" />

    <!-- 账单列表 -->
    <template v-else>
      <el-card v-for="b in bills" :key="b.billId" shadow="never" class="bill-card" @click="goToDetail(b.billId)">
        <div class="bill-card-body">
          <div class="bill-card-left">
            <div class="bill-station">{{ b.station?.name }}</div>
            <div class="bill-meta">
              <span>{{ b.chargingDuration }}</span>
              <span>{{ b.chargedEnergyKwh }} kWh</span>
              <span>{{ formatTime(b.createdAt) }}</span>
            </div>
          </div>
          <div class="bill-card-right">
            <div class="bill-amount">¥{{ b.totalFee.toFixed(2) }}</div>
            <el-tag :type="b.paymentStatus === 'paid' ? 'success' : 'warning'" size="small" effect="light">
              {{ b.paymentStatus === 'paid' ? '已支付' : '未支付' }}
            </el-tag>
          </div>
        </div>
      </el-card>

      <!-- 分页 -->
      <div class="pagination-wrapper" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchBills"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getBillsApi } from '@/api/bill'
import { formatTime } from '@/utils/format'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()
const bills = ref<any[]>([])
const loading = ref(true)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const filters = ref<{ paymentStatus?: string; startDate?: string; endDate?: string }>({})

async function fetchBills(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const params: any = { page: page.value, pageSize: pageSize.value }
    if (filters.value.paymentStatus) params.paymentStatus = filters.value.paymentStatus
    if (filters.value.startDate) params.startDate = filters.value.startDate
    if (filters.value.endDate) params.endDate = filters.value.endDate
    const res = await getBillsApi(params)
    const data = (res.data as any).data
    bills.value = data.list
    total.value = data.total
    page.value = data.page
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '加载账单失败')
  } finally { loading.value = false }
}

function resetFilters() {
  filters.value = {}
  fetchBills(1)
}

function goToDetail(id: number) {
  router.push(`/bills/${id}`)
}

onMounted(() => fetchBills(1))
</script>

<style scoped>
.bills-list { max-width: 640px; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-header h2 { font-size: 20px; font-weight: 600; color: #1E293B; margin: 0; }
.filter-card { border-radius: 10px; margin-bottom: 16px; }
.filter-card :deep(.el-form) { margin-bottom: -18px; }
.loading-wrapper { padding: 32px 0; }
.bill-card { border-radius: 10px; margin-bottom: 12px; cursor: pointer; transition: box-shadow 0.2s; }
.bill-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.bill-card-body { display: flex; justify-content: space-between; align-items: center; }
.bill-card-left { display: flex; flex-direction: column; gap: 4px; }
.bill-station { font-size: 15px; font-weight: 600; color: #1E293B; }
.bill-meta { display: flex; gap: 12px; font-size: 12px; color: #94A3B8; }
.bill-card-right { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.bill-amount { font-size: 20px; font-weight: 700; color: #1E293B; font-family: 'JetBrains Mono', monospace; }
.pagination-wrapper { display: flex; justify-content: center; margin-top: 20px; }
</style>
