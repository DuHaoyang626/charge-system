<template>
  <div class="bills-list">
    <div class="page-header-responsive">
      <div>
        <h2>📋 历史账单</h2>
        <p class="page-desc">共 {{ total }} 条记录</p>
      </div>
      <span class="glass-badge hide-xs">共 {{ total }} 条</span>
    </div>

    <div class="glass-card filter-card">
      <el-form :inline="true" size="small" class="responsive-flex">
        <el-form-item label="支付状态">
          <el-select v-model="filters.paymentStatus" placeholder="全部" clearable style="width:120px" @change="fetchBills(1)">
            <el-option label="未支付" value="unpaid" /><el-option label="已支付" value="paid" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="filters.startDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:clamp(120px,15vw,140px)" @change="fetchBills(1)" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="filters.endDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:clamp(120px,15vw,140px)" @change="fetchBills(1)" />
        </el-form-item>
        <el-form-item><button class="btn-glass btn-glass-sm" @click="resetFilters">🔄 重置</button></el-form-item>
      </el-form>
    </div>

    <div v-if="loading" class="loading-wrapper"><el-skeleton :rows="3" animated /></div>
    <div v-else-if="!bills.length" class="glass-card" style="padding:0;"><EmptyState icon="Document" description="暂无账单记录" /></div>
    <template v-else>
      <div v-for="b in bills" :key="b.billId" class="glass-card bill-card" @click="goToDetail(b.billId)">
        <div class="bill-card-body">
          <div class="bill-card-left">
            <div class="bill-station">{{ b.station?.name }}</div>
            <div class="bill-meta">
              <span>⏱ {{ b.chargingDuration }}</span>
              <span>⚡ {{ b.chargedEnergyKwh }} kWh</span>
              <span class="hide-xs">📅 {{ formatTime(b.createdAt) }}</span>
            </div>
          </div>
          <div class="bill-card-right">
            <div class="bill-amount">¥{{ b.totalFee.toFixed(2) }}</div>
            <el-tag :type="b.paymentStatus === 'paid' ? 'success' : 'warning'" size="small" effect="light">
              {{ b.paymentStatus === 'paid' ? '✅ 已支付' : '⏳ 未支付' }}
            </el-tag>
          </div>
        </div>
      </div>
      <div class="pagination-wrapper" v-if="total > pageSize">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="fetchBills" />
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
    bills.value = data.list; total.value = data.total; page.value = data.page
  } catch (err: any) { ElMessage.error(err?.response?.data?.message || '加载账单失败') }
  finally { loading.value = false }
}
function resetFilters() { filters.value = {}; fetchBills(1) }
function goToDetail(id: number) { router.push(`/bills/${id}`) }
onMounted(() => fetchBills(1))
</script>

<style scoped>
.bills-list { max-width: 720px; margin: 0 auto; }
.filter-card { padding: clamp(12px, 1.5vw, 16px); margin-bottom: 16px; }
.loading-wrapper { padding: 32px 0; }
.bill-card { padding: clamp(14px, 1.5vw, 20px); margin-bottom: 12px; cursor: pointer; transition: all 0.3s ease; }
.bill-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg), var(--shadow-glass); }
.bill-card-body { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.bill-card-left { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.bill-station { font-size: clamp(14px, 1.3vw, 15px); font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bill-meta { display: flex; gap: clamp(8px, 1vw, 12px); font-size: clamp(11px, 1vw, 12px); color: var(--text-tertiary); flex-wrap: wrap; }
.bill-card-right { text-align: right; flex-shrink: 0; }
.bill-amount { font-size: clamp(17px, 2vw, 20px); font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
.pagination-wrapper { display: flex; justify-content: center; margin-top: 20px; }
</style>
