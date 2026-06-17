<template>
  <div class="auth-page">
    <el-card class="auth-card" shadow="never">
      <h2 class="auth-title">注册</h2>
      <p class="auth-subtitle">录入车辆信息创建账号</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleRegister"
      >
        <el-form-item label="车牌号" prop="licensePlate">
          <el-input
            v-model="form.licensePlate"
            placeholder="如 京A12345"
            maxlength="20"
          />
        </el-form-item>

        <el-form-item label="用户昵称" prop="userName">
          <el-input
            v-model="form.userName"
            placeholder="如 我的电车"
            maxlength="50"
          />
        </el-form-item>

        <el-form-item label="电池容量 (kWh)" prop="batteryCapacity">
          <el-input
            v-model.number="form.batteryCapacity"
            type="number"
            min="1"
            max="200"
            step="0.1"
            placeholder="请输入电池容量，如 60"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="支持的充电协议" prop="protocolIds">
          <el-select
            v-model="form.protocolIds"
            multiple
            placeholder="请选择充电协议"
            style="width: 100%"
          >
            <el-option
              v-for="p in protocols"
              :key="p.id"
              :label="`${p.name} (${p.powerKw}kW)`"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="不少于 6 位"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="再次输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="手机号（选填）" prop="phone">
          <el-input
            v-model="form.phone"
            placeholder="选填"
            maxlength="20"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="loading"
            class="submit-btn"
          >
            {{ loading ? '注册中...' : '注册' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        已有账号？
        <router-link to="/login">去登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getProtocolsApi } from '@/api/auth'
import type { ProtocolOption } from '@/api/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const protocols = ref<ProtocolOption[]>([])

const form = reactive({
  licensePlate: '',
  userName: '',
  batteryCapacity: 60,
  protocolIds: [] as number[],
  password: '',
  confirmPassword: '',
  phone: '',
})

/** 确认密码自定义校验 */
const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.password) {
    callback(new Error('两次密码输入不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  licensePlate: [
    { required: true, message: '请输入车牌号', trigger: 'blur' },
    { min: 2, max: 20, message: '车牌号长度 2~20 位', trigger: 'blur' },
  ],
  userName: [
    { required: true, message: '请输入用户昵称', trigger: 'blur' },
  ],
  batteryCapacity: [
    { required: true, message: '请输入电池容量', trigger: 'blur' },
    { type: 'number', min: 1, max: 200, message: '电池容量必须在 1~200 kWh 之间', trigger: 'blur' },
  ],
  protocolIds: [
    { required: true, message: '请至少选择一个充电协议', trigger: 'change' },
    { type: 'array', min: 1, message: '请至少选择一个充电协议', trigger: 'change' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不少于 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleRegister() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.register({
      licensePlate: form.licensePlate,
      userName: form.userName,
      batteryCapacity: form.batteryCapacity,
      password: form.password,
      confirmPassword: form.confirmPassword,
      protocolIds: form.protocolIds,
      phone: form.phone || undefined,
    })
    ElMessage.success('注册成功')
    router.push('/')
  } catch (err: any) {
    const msg = err?.response?.data?.message || '注册失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const res = await getProtocolsApi()
    const body = res.data as any
    protocols.value = body.data || body
  } catch {
    // 如果 /protocols 接口未实现则使用静态数据
    protocols.value = [
      { id: 1, name: 'AC 7kW', powerKw: 7.0 },
      { id: 2, name: 'DC 22kW', powerKw: 22.0 },
      { id: 3, name: 'DC 50kW', powerKw: 50.0 },
      { id: 4, name: 'DC 120kW', powerKw: 120.0 },
      { id: 5, name: 'DC 250kW', powerKw: 250.0 },
    ]
  }
})
</script>

<style scoped>
.auth-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F5F5F5;
  padding: 24px;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 32px 24px;
  border-radius: 12px;
}

.auth-title {
  font-size: 24px;
  font-weight: 600;
  color: #1A1A1A;
  margin-bottom: 4px;
}

.auth-subtitle {
  font-size: 14px;
  color: #737373;
  margin-bottom: 24px;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

.auth-footer {
  text-align: center;
  font-size: 14px;
  color: #737373;
  margin-top: 16px;
}

.auth-footer a {
  color: #2563EB;
  font-weight: 500;
}
</style>
