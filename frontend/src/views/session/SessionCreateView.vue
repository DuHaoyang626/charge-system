<template>
  <div class="session-create">
    <h2 class="page-title">⚡ 发起充电请求</h2>
    <div class="glass-card create-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleCreate">
        <el-form-item label="目标充电量 (kWh)" prop="requestedEnergyKwh">
          <el-input v-model.number="form.requestedEnergyKwh" type="number" :min="1" step="0.1" placeholder="如 60" class="glass-input">
            <template #append>kWh</template>
          </el-input>
          <div class="form-tip" v-if="user?.batteryCapacity">🔋 您的电池容量为 {{ user.batteryCapacity }} kWh</div>
        </el-form-item>
        <el-form-item label="充电协议" prop="protocolIds">
          <el-select v-model="form.protocolIds" multiple placeholder="选择本次充电支持的协议" style="width:100%" class="glass-input">
            <el-option v-for="p in userProtocols" :key="p.id" :label="`${p.name} (${p.powerKw}kW)`" :value="p.id" />
          </el-select>
          <div class="form-tip">至少选择一个，系统将自动匹配最优充电桩</div>
        </el-form-item>
        <el-alert type="info" :closable="false" show-icon class="info-alert" style="border:none;padding:12px 16px;margin-bottom:16px;border-radius:var(--radius-md);">
          <template #title>🤖 系统将自动计算最佳充电桩，您无需手动选择</template>
        </el-alert>
        <el-form-item>
          <button type="submit" :disabled="loading" class="btn-glass btn-glass-primary btn-glass-lg submit-btn">
            {{ loading ? '⏳ 提交中...' : '⚡ 提交充电请求' }}
          </button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { createSessionApi } from '@/api/session'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const user = computed(() => auth.user)
const userProtocols = computed(() => user.value?.protocols || [])
const form = reactive({ requestedEnergyKwh: 60, protocolIds: [] as number[] })
const rules: FormRules = {
  requestedEnergyKwh: [{ required: true, message: '请输入目标充电量', trigger: 'blur' }, { type: 'number', min: 0.1, message: '充电量必须大于 0', trigger: 'blur' }],
  protocolIds: [{ required: true, message: '请至少选择一个协议', trigger: 'change' }, { type: 'array', min: 1, message: '请至少选择一个协议', trigger: 'change' }],
}

async function handleCreate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const res = await createSessionApi({ requestedEnergyKwh: form.requestedEnergyKwh, protocolIds: form.protocolIds })
    const body = res.data as any
    if (body.code === 201) {
      ElMessage.success('🎉 充电请求已提交')
      router.push(`/sessions/${body.data.sessionId}`)
    } else ElMessage.error(body.message || '提交失败')
  } catch (err: any) { ElMessage.error(err?.response?.data?.message || '发起充电请求失败') }
  finally { loading.value = false }
}
</script>

<style scoped>
.session-create { max-width: min(92vw, 520px); margin: 0 auto; }
.page-title { font-size: clamp(20px, 2.5vw, 24px); font-weight: 700; color: var(--text-primary); margin-bottom: clamp(16px, 2vw, 20px); }
.create-card { padding: clamp(20px, 3vw, 28px); }
.form-tip { font-size: clamp(11px, 1vw, 12px); color: var(--text-tertiary); margin-top: 4px; }
.submit-btn { width: 100%; margin-top: 8px; }
</style>
