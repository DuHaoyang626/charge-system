<template>
  <div class="auth-page-responsive glass-container">
    <div class="auth-card-responsive glass-card-strong" style="background:var(--bg-glass-strong);">
      <div class="login-header">
        <div class="admin-badge">ADMIN</div>
        <h2 class="auth-title">管理后台登录</h2>
        <p class="auth-subtitle">充电桩调度计费系统 · 管理端</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="管理员账号" prop="licensePlate">
          <el-input v-model="form.licensePlate" placeholder="输入管理员车牌号" :prefix-icon="User" class="glass-input" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="输入密码" show-password :prefix-icon="Lock" class="glass-input" />
        </el-form-item>
        <el-form-item>
          <button type="submit" :disabled="loading" class="btn-glass btn-glass-lg submit-btn" style="background:var(--color-danger);color:#fff;border:none;width:100%;">
            {{ loading ? '⏳ 验证中...' : '🔐 进入管理后台' }}
          </button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        <router-link to="/login">普通用户登录 →</router-link>
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
const form = reactive({ licensePlate: 'ADMIN', password: 'admin123' })
const rules: FormRules = {
  licensePlate: [{ required: true, message: '请输入管理员账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const result = await auth.login({ licensePlate: form.licensePlate, password: form.password })
    if (result.role !== 'admin') {
      ElMessage.error('该账号不是管理员，请使用普通用户登录')
      auth.logout(); return
    }
    ElMessage.success('👋 欢迎回来')
    router.push('/admin/dashboard')
  } catch (err: any) { ElMessage.error(err?.response?.data?.message || '账号或密码错误') }
  finally { loading.value = false }
}
</script>

<style scoped>
.login-header { text-align: center; margin-bottom: clamp(20px, 3vw, 32px); }
.admin-badge { display: inline-block; background: #DC2626; color: #FFFFFF; font-size: 11px; font-weight: 700; padding: 3px 14px; border-radius: 10px; letter-spacing: 1px; margin-bottom: 14px; }
.auth-title { font-size: clamp(20px, 3vw, 24px); color: var(--text-primary); font-weight: 700; margin-bottom: 6px; }
.auth-subtitle { font-size: clamp(12px, 1.2vw, 13px); color: var(--text-tertiary); }
.submit-btn { width: 100%; }
.auth-footer { text-align: center; margin-top: 20px; }
.auth-footer a { font-size: 13px; color: var(--text-tertiary); }
.auth-footer a:hover { color: var(--color-primary); }
</style>
