<template>
  <div class="bill-detail">
    <el-skeleton v-if="loading && !bill" :rows="6" animated />

    <div v-else-if="error" class="glass-card result-card">
      <div class="result-icon">❌</div>
      <h3>加载失败</h3>
      <p class="info-text">{{ error }}</p>
      <div class="action-row">
        <button class="btn-glass btn-glass-primary" @click="fetchBill">🔄 重试</button>
        <button class="btn-glass" @click="goBack">← 返回</button>
      </div>
    </div>

    <template v-else-if="bill">
      <div class="bill-header">
        <button class="btn-glass btn-glass-sm" @click="goBack">← 返回</button>
        <el-tag :type="bill.paymentStatus === 'paid' ? 'success' : 'warning'" effect="dark" size="large">
          {{ bill.paymentStatus === 'paid' ? '✅ 已支付' : '⏳ 未支付' }}
        </el-tag>
      </div>

      <div class="glass-card total-card">
        <div class="total-amount">¥{{ bill.totalFee.toFixed(2) }}</div>
        <p class="total-label">总费用</p>
        <div class="total-meta">
          <span class="glass-badge">{{ bill.station?.name }}</span>
          <span class="glass-badge">⏱ {{ bill.chargingDuration }}</span>
          <span class="glass-badge">⚡ {{ bill.chargedEnergyKwh }} kWh</span>
        </div>
      </div>

      <div class="glass-card section-card">
        <div class="section-header-row"><span>⚡ 电费明细</span><span class="section-total">¥{{ bill.electricityFee.toFixed(2) }}</span></div>
        <div class="detail-list">
          <div v-for="item in bill.electricityDetails" :key="item.period" class="detail-row">
            <span class="detail-name">{{ item.period }}</span>
            <div class="detail-right"><span class="detail-quantity">{{ item.energy }} kWh</span><span class="detail-price">× ¥{{ item.price }}</span><span class="detail-fee">= ¥{{ item.fee.toFixed(2) }}</span></div>
          </div>
        </div>
      </div>

      <div class="glass-card section-card">
        <div class="section-header-row"><span>💰 服务费明细</span><span class="section-total">¥{{ bill.totalServiceFee.toFixed(2) }}</span></div>
        <div class="detail-list">
          <div v-for="item in bill.serviceFeeTiers" :key="item.tier" class="detail-row">
            <span class="detail-name">{{ item.tier }}</span>
            <div class="detail-right"><span v-if="item.minutes > 0" class="detail-quantity">{{ item.minutes }} 分钟</span><span class="detail-price">× ¥{{ item.rate }}</span><span class="detail-fee">= ¥{{ item.fee.toFixed(2) }}</span></div>
          </div>
        </div>
      </div>

      <div class="glass-card info-card">
        <div class="info-row"><span>账单编号</span><span>{{ bill.id }}</span></div>
        <div class="info-row"><span>关联会话</span><span>{{ bill.sessionId }}</span></div>
        <div class="info-row"><span>充电桩</span><span>{{ bill.station?.name }}</span></div>
        <div class="info-row"><span>充电时长</span><span>{{ bill.chargingDuration }}</span></div>
        <div class="info-row"><span>充电电量</span><span>{{ bill.chargedEnergyKwh }} kWh</span></div>
        <div class="info-row"><span>创建时间</span><span>{{ formatTime(bill.createdAt) }}</span></div>
        <div class="info-row" v-if="bill.paidAt"><span>支付时间</span><span>{{ formatTime(bill.paidAt) }}</span></div>
        <div class="info-row" v-if="bill.transactionId"><span>交易流水</span><span class="txn-id">{{ bill.transactionId }}</span></div>
      </div>

      <div v-if="bill.paymentStatus === 'unpaid'" class="glass-card pay-section">
        <div class="pay-row">
          <span class="pay-label">选择支付方式</span>
          <el-radio-group v-model="paymentMethod" class="pay-methods">
            <el-radio value="wechat" border class="glass-badge">微信支付</el-radio>
            <el-radio value="alipay" border class="glass-badge">支付宝</el-radio>
            <el-radio value="card" border class="glass-badge">银行卡</el-radio>
          </el-radio-group>
        </div>
        <div class="pay-action">
          <button class="btn-glass btn-glass-primary btn-glass-lg pay-btn" :disabled="!paymentMethod || payLoading" @click="handlePay">
            {{ payLoading ? '⏳ 支付中...' : `💳 确认支付 ¥${bill.totalFee.toFixed(2)}` }}
          </button>
        </div>
      </div>

      <div v-if="showPaySuccess" class="glass-card result-card">
        <div class="result-icon">✅</div>
        <h3>支付成功</h3>
        <p class="info-text">交易流水号：{{ payResult?.transactionId }}</p>
        <p class="info-text">支付金额：¥{{ payResult?.totalFee.toFixed(2) }}</p>
        <p class="info-text">支付时间：{{ formatTime(payResult?.paidAt) }}</p>
        <div class="action-row">
          <button class="btn-glass btn-glass-primary" @click="goToBillList">📋 查看历史账单</button>
          <button class="btn-glass" @click="goHome">🏠 返回主页</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
  loading.value = true; error.value = ''
  try {
    const res = await getBillDetailApi(id)
    bill.value = (res.data as any).data
  } catch (err: any) {
    if (err?.response?.status === 404) error.value = '账单不存在'
    else if (err?.response?.status === 403) error.value = '无权访问该账单'
    else error.value = err?.response?.data?.message || '加载失败'
  } finally { loading.value = false }
}

async function handlePay() {
  if (!paymentMethod.value) { ElMessage.warning('请选择支付方式'); return }
  payLoading.value = true
  try {
    await ElMessageBox.confirm(`确认支付 ¥${bill.value.totalFee.toFixed(2)}？`, '支付确认', { confirmButtonText: '确定支付', cancelButtonText: '取消', type: 'info' })
    const res = await payBillApi(bill.value.id, paymentMethod.value)
    payResult.value = (res.data as any).data; showPaySuccess.value = true
    ElMessage.success('🎉 支付成功')
  } catch (err: any) { if (err?.code !== 'cancel') ElMessage.error(err?.response?.data?.message || '支付失败') }
  finally { payLoading.value = false }
}

function goBack() { router.back() }
function goHome() { router.push('/') }
function goToBillList() { router.push('/bills') }
onMounted(fetchBill)
</script>

<style scoped>
.bill-detail { max-width: min(92vw, 580px); margin: 0 auto; display: flex; flex-direction: column; gap: clamp(12px, 1.5vw, 16px); }
.bill-header { display: flex; align-items: center; justify-content: space-between; }
.total-card { text-align: center; padding: clamp(24px, 4vw, 32px) clamp(16px, 2vw, 24px); }
.total-amount { font-size: clamp(36px, 6vw, 48px); font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
.total-label { font-size: 14px; color: var(--text-tertiary); margin-top: 4px; }
.total-meta { display: flex; justify-content: center; gap: clamp(8px, 1vw, 12px); margin-top: 16px; flex-wrap: wrap; }
.section-card { padding: clamp(16px, 2vw, 20px); }
.section-header-row { font-weight: 600; font-size: clamp(14px, 1.3vw, 15px); color: var(--text-primary); display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 4px; }
.section-total { font-weight: 700; color: var(--color-danger); font-family: 'JetBrains Mono', monospace; font-size: clamp(14px, 1.3vw, 16px); }
.detail-list { display: flex; flex-direction: column; gap: 6px; }
.detail-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; gap: 8px; flex-wrap: wrap; }
.detail-name { font-size: clamp(13px, 1.1vw, 14px); color: var(--text-secondary); }
.detail-right { display: flex; align-items: center; gap: clamp(6px, 0.8vw, 8px); font-family: 'JetBrains Mono', monospace; font-size: clamp(12px, 1vw, 13px); flex-wrap: wrap; justify-content: flex-end; }
.detail-quantity { color: var(--text-tertiary); }
.detail-price { color: var(--text-tertiary); }
.detail-fee { color: var(--text-primary); font-weight: 600; min-width: 60px; text-align: right; }
.info-card { padding: clamp(16px, 2vw, 20px); }
.info-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: clamp(13px, 1.1vw, 14px); color: var(--text-secondary); gap: 12px; }
.info-row span:first-child { color: var(--text-tertiary); flex-shrink: 0; }
.info-row span:last-child { text-align: right; min-width: 0; }
.txn-id { color: var(--color-primary); font-family: 'JetBrains Mono', monospace; font-size: 12px; word-break: break-all; }
.pay-section { padding: clamp(16px, 2vw, 24px); }
.pay-row { margin-bottom: 16px; }
.pay-label { font-size: 14px; color: var(--text-secondary); margin-bottom: 8px; display: block; }
.pay-methods { display: flex; gap: 8px; flex-wrap: wrap; }
.pay-methods .el-radio { margin-right: 0; }
.pay-action { text-align: center; }
.pay-btn { width: 100%; max-width: 360px; }
.result-card { text-align: center; padding: clamp(32px, 6vw, 48px) clamp(16px, 2vw, 24px); }
.result-icon { font-size: clamp(48px, 8vw, 64px); margin-bottom: 16px; }
.result-card h3 { font-size: clamp(20px, 3vw, 24px); font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.info-text { font-size: clamp(13px, 1.1vw, 14px); color: var(--text-tertiary); }
.action-row { display: flex; justify-content: center; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
</style>
