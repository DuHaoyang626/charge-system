<template>
  <div class="auth-page-responsive glass-container">
    <div class="auth-card-responsive glass-card-strong">
      <div class="auth-header">
        <div class="auth-logo">⚡</div>
        <h2 class="auth-title">欢迎回来</h2>
        <p class="auth-subtitle">输入车牌号和密码登录系统</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="车牌号" prop="licensePlate">
          <el-input v-model="form.licensePlate" placeholder="请输入车牌号，如 京A12345" maxlength="20" :prefix-icon="User" class="glass-input" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password :prefix-icon="Lock" class="glass-input" />
        </el-form-item>
        <el-form-item>
          <button type="submit" :disabled="loading" class="btn-glass btn-glass-primary btn-glass-lg submit-btn">
            {{ loading ? '⏳ 登录中...' : '🔑 登录' }}
          </button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        没有账号？<router-link to="/register">去注册 →</router-link>
      </div>
    </div>
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

const form = reactive({ licensePlate: '', password: '' })

const rules: FormRules = {
  licensePlate: [{ required: true, message: '请输入车牌号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码长度不少于 6 位', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await auth.login({ licensePlate: form.licensePlate, password: form.password })
    ElMessage.success('🎉 登录成功')
    router.push('/')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '账号或密码错误')
  } finally { loading.value = false }
}
</script>

<style scoped>
.auth-header { text-align: center; margin-bottom: clamp(20px, 3vw, 32px); }
.auth-logo { font-size: clamp(36px, 6vw, 48px); margin-bottom: 12px; }
.auth-title { font-size: clamp(22px, 3.5vw, 26px); font-weight: 700; color: var(--text-primary); margin-bottom: 6px; }
.auth-subtitle { font-size: clamp(13px, 1.2vw, 14px); color: var(--text-tertiary); }
.submit-btn { width: 100%; margin-top: 8px; }
.auth-footer { text-align: center; font-size: 14px; color: var(--text-tertiary); margin-top: 20px; }
.auth-footer a { color: var(--color-primary); font-weight: 600; }
</style>
