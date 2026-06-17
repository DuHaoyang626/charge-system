<template>
  <div class="bill-detail" v-loading="loading">
    <!-- 加载中 -->
    <el-skeleton v-if="loading && !bill" :rows="6" animated />

    <!-- 错误状态 -->
    <el-result v-else-if="error" icon="error" title="加载失败" :sub-title="error">
      <template #extra>
        <el-button type="primary" @click="fetchBill">重试</el-button>
        <el-button @click="goBack">返回</el-button>
      </template>
    </el-result>

    <template v-else-if="bill">
      <!-- 头部 -->
      <div class="bill-header">
        <el-button text @click="goBack"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <el-tag :type="bill.paymentStatus === 'paid' ? 'success' : 'warning'" effect="dark" size="large">
          {{ bill.paymentStatus === 'paid' ? '已支付' : '未支付' }}
        </el-tag>
      </div>

      <!-- 总费用卡片 -->
      <el-card shadow="never" class="total-card">
        <div class="total-amount">¥{{ bill.totalFee.toFixed(2) }}</div>
        <p class="total-label">总费用</p>
        <div class="total-meta">
          <span>{{ bill.station?.name }}</span>
          <span>{{ bill.chargingDuration }}</span>
          <span>{{ bill.chargedEnergyKwh }} kWh</span>
        </div>
      </el-card>

      <!-- 电费明细 -->
      <el-card shadow="never" class="section-card">
        <template #header>电费明细 <span class="section-total">¥{{ bill.electricityFee.toFixed(2) }}</span></template>
        <div class="detail-list">
          <div v-for="item in bill.electricityDetails" :key="item.period" class="detail-row">
            <div class="detail-left">
              <span class="detail-name">{{ item.period }}</span>
            </div>
            <div class="detail-right">
              <span class="detail-quantity">{{ item.energy }} kWh</span>
              <span class="detail-price">× ¥{{ item.price }}</span>
              <span class="detail-fee">= ¥{{ item.fee.toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 服务费明细 -->
      <el-card shadow="never" class="section-card">
        <template #header>服务费明细 <span class="section-total">¥{{ bill.totalServiceFee.toFixed(2) }}</span></template>
        <div class="detail-list">
          <div v-for="item in bill.serviceFeeTiers" :key="item.tier" class="detail-row">
            <div class="detail-left">
              <span class="detail-name">{{ item.tier }}</span>
            </div>
            <div class="detail-right">
              <span v-if="item.minutes > 0" class="detail-quantity">{{ item.minutes }} 分钟</span>
              <span class="detail-price">× ¥{{ item.rate }}</span>
              <span class="detail-fee">= ¥{{ item.fee.toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 补充信息 -->
      <el-card shadow="never" class="info-card">
        <div class="info-row"><span>账单编号</span><span>{{ bill.id }}</span></div>
        <div class="info-row"><span>关联会话</span><span>{{ bill.sessionId }}</span></div>
        <div class="info-row"><span>充电桩</span><span>{{ bill.station?.name }}</span></div>
        <div class="info-row"><span>充电时长</span><span>{{ bill.chargingDuration }}</span></div>
        <div class="info-row"><span>充电电量</span><span>{{ bill.chargedEnergyKwh }} kWh</span></div>
        <div class="info-row"><span>创建时间</span><span>{{ formatTime(bill.createdAt) }}</span></div>
        <div class="info-row" v-if="bill.paidAt"><span>支付时间</span><span>{{ formatTime(bill.paidAt) }}</span></div>
        <div class="info-row" v-if="bill.transactionId"><span>交易流水</span><span class="txn-id">{{ bill.transactionId }}</span></div>
      </el-card>

      <!-- 支付按钮 -->
      <div class="pay-section" v-if="bill.paymentStatus === 'unpaid'">
        <el-card shadow="never">
          <div class="pay-row">
            <span class="pay-label">选择支付方式</span>
            <el-radio-group v-model="paymentMethod" class="pay-methods">
              <el-radio value="wechat" border class="pay-method-option">微信支付</el-radio>
              <el-radio value="alipay" border class="pay-method-option">支付宝</el-radio>
              <el-radio value="card" border class="pay-method-option">银行卡</el-radio>
            </el-radio-group>
          </div>
          <div class="pay-action">
            <el-button type="primary" size="large" :loading="payLoading" :disabled="!paymentMethod"
              @click="handlePay" class="pay-btn">
              确认支付 ¥{{ bill.totalFee.toFixed(2) }}
            </el-button>
          </div>
        </el-card>
      </div>

      <!-- 支付成功 -->
      <el-result v-if="showPaySuccess" icon="success" title="支付成功">
        <template #sub-title>
          <p>交易流水号：{{ payResult?.transactionId }}</p>
          <p>支付金额：¥{{ payResult?.totalFee.toFixed(2) }}</p>
          <p>支付时间：{{ formatTime(payResult?.paidAt) }}</p>
        </template>
        <template #extra>
          <el-button type="primary" @click="goToBillList">查看历史账单</el-button>
          <el-button @click="goHome">返回主页</el-button>
        </template>
      </el-result>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getBillDetailApi, payBillApi } from '@/api/bill'
import { formatTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const bill = ref<any>(null)
const loading = ref(true)
const error = ref('')
const paymentMethod = ref('wechat')
const payLoading = ref(false)
const showPaySuccess = ref(false)
const payResult = ref<any>(null)

async function fetchBill() {
  const id = Number(route.params.id)
  if (!id) { error.value = '无效的账单ID'; loading.value = false; return }
  loading.value = true
  error.value = ''
  try {
    const res = await getBillDetailApi(id)
    bill.value = (res.data as any).data
  } catch (err: any) {
    if (err?.response?.status === 404) {
      error.value = '账单不存在'
    } else if (err?.response?.status === 403) {
      error.value = '无权访问该账单'
    } else {
      error.value = err?.response?.data?.message || '加载失败'
    }
  } finally { loading.value = false }
}

async function handlePay() {
  if (!paymentMethod.value) {
    ElMessage.warning('请选择支付方式')
    return
  }
  payLoading.value = true
  try {
    await ElMessageBox.confirm(
      `确认支付 ¥${bill.value.totalFee.toFixed(2)}？`,
      '支付确认',
      { confirmButtonText: '确定支付', cancelButtonText: '取消', type: 'info' }
    )
    const res = await payBillApi(bill.value.id, paymentMethod.value)
    payResult.value = (res.data as any).data
    showPaySuccess.value = true
    ElMessage.success('支付成功')
  } catch (err: any) {
    if (err?.code !== 'cancel') {
      ElMessage.error(err?.response?.data?.message || '支付失败')
    }
  } finally { payLoading.value = false }
}

function goBack() { router.back() }
function goHome() { router.push('/') }
function goToBillList() { router.push('/bills') }

onMounted(fetchBill)
</script>

<style scoped>
.bill-detail { max-width: 560px; margin: 0 auto; }
.bill-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.total-card { border-radius: 12px; text-align: center; padding: 32px 24px; }
.total-amount { font-size: 48px; font-weight: 700; color: #1E293B; font-family: 'JetBrains Mono', monospace; }
.total-label { font-size: 14px; color: #64748B; margin-top: 4px; }
.total-meta { display: flex; justify-content: center; gap: 16px; margin-top: 12px; font-size: 13px; color: #94A3B8; }
.section-card { border-radius: 12px; margin-top: 16px; }
.section-card :deep(.el-card__header) { font-weight: 600; font-size: 15px; color: #1E293B; display: flex; justify-content: space-between; align-items: center; }
.section-total { font-weight: 700; color: #EA580C; font-family: 'JetBrains Mono', monospace; font-size: 16px; }
.detail-list { display: flex; flex-direction: column; gap: 8px; }
.detail-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
.detail-left { flex-shrink: 0; }
.detail-name { font-size: 14px; color: #475569; }
.detail-right { display: flex; align-items: center; gap: 8px; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.detail-quantity { color: #64748B; }
.detail-price { color: #94A3B8; }
.detail-fee { color: #1E293B; font-weight: 600; min-width: 60px; text-align: right; }
.info-card { border-radius: 12px; margin-top: 16px; }
.info-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; color: #475569; }
.info-row span:first-child { color: #94A3B8; }
.txn-id { color: #2563EB; font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.pay-section { margin-top: 20px; }
.pay-section .el-card { border-radius: 12px; }
.pay-row { margin-bottom: 16px; }
.pay-label { font-size: 14px; color: #475569; margin-bottom: 8px; display: block; }
.pay-methods { display: flex; gap: 8px; flex-wrap: wrap; }
.pay-method-option { margin-right: 0; border-radius: 8px; padding: 8px 16px; }
.pay-action { text-align: center; }
.pay-btn { width: 100%; max-width: 320px; }
</style>
