<template>
  <div class="admin-login-page">
    <el-card class="admin-login-card" shadow="never">
      <div class="login-header">
        <div class="admin-badge">ADMIN</div>
        <h2>管理后台登录</h2>
        <p class="login-desc">充电桩调度计费系统 · 管理端</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="管理员账号" prop="licensePlate">
          <el-input
            v-model="form.licensePlate"
            placeholder="输入管理员车牌号"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="输入密码"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="danger" native-type="submit" :loading="loading" class="submit-btn">
            {{ loading ? '验证中...' : '进入管理后台' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <router-link to="/login">普通用户登录 →</router-link>
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
  licensePlate: 'ADMIN',
  password: 'admin123',
})

const rules: FormRules = {
  licensePlate: [{ required: true, message: '请输入管理员账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const result = await auth.login({
      licensePlate: form.licensePlate,
      password: form.password,
    })
    if (result.role !== 'admin') {
      ElMessage.error('该账号不是管理员，请使用普通用户登录')
      auth.logout()
      return
    }
    ElMessage.success('欢迎回来')
    router.push('/admin/dashboard')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '账号或密码错误')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-login-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0F172A;
  padding: 24px;
}

.admin-login-card {
  width: 100%;
  max-width: 400px;
  padding: 32px 24px;
  border-radius: 12px;
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.admin-badge {
  display: inline-block;
  background: #DC2626;
  color: #FFFFFF;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 12px;
  border-radius: 10px;
  letter-spacing: 1px;
  margin-bottom: 12px;
}

.login-header h2 {
  font-size: 22px;
  color: #1A1A1A;
  font-weight: 600;
  margin-bottom: 4px;
}

.login-desc {
  font-size: 13px;
  color: #94A3B8;
}

.submit-btn {
  width: 100%;
}

.login-footer {
  text-align: center;
  margin-top: 16px;
}

.login-footer a {
  font-size: 13px;
  color: #64748B;
}
</style>
