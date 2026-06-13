<template>
  <div class="auth-page">
    <el-card class="auth-card" shadow="never">
      <h2 class="auth-title">登录</h2>
      <p class="auth-subtitle">输入车牌号和密码登录系统</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="车牌号" prop="licensePlate">
          <el-input
            v-model="form.licensePlate"
            placeholder="请输入车牌号，如 京A12345"
            maxlength="20"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="loading"
            class="submit-btn"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        没有账号？
        <router-link to="/register">去注册</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  licensePlate: '',
  password: '',
})

const rules: FormRules = {
  licensePlate: [
    { required: true, message: '请输入车牌号', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不少于 6 位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.login({
      licensePlate: form.licensePlate,
      password: form.password,
    })
    ElMessage.success('登录成功')
    router.push('/')
  } catch (err: any) {
    const msg = err?.response?.data?.message || '账号或密码错误'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
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
