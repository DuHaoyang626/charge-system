<template>
  <div class="station-manage">
    <!-- 页面标题 -->
    <div class="page-header">
      <div>
        <h2>充电桩管理</h2>
        <p class="page-desc">创建、修改、删除充电桩，控制启停</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新建充电桩</el-button>
    </div>

    <!-- 列表表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="stations" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <StationStatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="三区容量" min-width="200">
          <template #default="{ row }">
            <div class="zone-info">
              <span>🚶 {{ row.queueCount }}/{{ row.queueCapacity }}</span>
              <span>⏳ {{ row.waitingCount }}/{{ row.waitingCapacity }}</span>
              <span>⚡ {{ row.chargingCount }}/{{ row.chargingCapacity }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="支持协议" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="p in row.supportedProtocols" :key="p.id" size="small" effect="plain" class="proto-tag">
              {{ p.name }}
            </el-tag>
            <span v-if="!row.supportedProtocols?.length" class="no-data">--</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="openEdit(row)">编辑</el-button>
            <el-button
              size="small" text
              :type="row.status === 'running' ? 'warning' : 'success'"
              @click="handleToggleStatus(row)"
            >
              {{ row.status === 'running' ? '停止' : '启动' }}
            </el-button>
            <el-popconfirm
              v-if="row.status === 'running'"
              title="紧急停止后排队/等待/充电中车辆全部重调度到其他桩，确定？"
              confirm-button-text="紧急停止"
              @confirm="handleEmergencyStop(row)"
            >
              <template #reference>
                <el-button size="small" text type="danger">紧急停止</el-button>
              </template>
            </el-popconfirm>
            <el-popconfirm
              title="确定删除此充电桩？"
              :confirm-button-text="'删除'"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button size="small" text type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ═══════════ 创建/编辑对话框 ═══════════ -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑充电桩' : '新建充电桩'"
      :width="520"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="充电桩名称" prop="name">
          <el-input v-model="form.name" placeholder="如 C区-03号桩" />
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="排队区容量" prop="queueCapacity">
              <el-input-number v-model="form.queueCapacity" :min="1" :max="50" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="等待区容量" prop="waitingCapacity">
              <el-input-number v-model="form.waitingCapacity" :min="1" :max="20" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="充电区容量" prop="chargingCapacity">
              <el-input-number v-model="form.chargingCapacity" :min="1" :max="10" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="支持协议" prop="protocolIds">
          <el-select v-model="form.protocolIds" multiple placeholder="请选择协议" style="width: 100%">
            <el-option
              v-for="p in protocols"
              :key="p.id"
              :label="`${p.name} (${p.powerKw}kW)`"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="基础服务费（元/次）" prop="baseServiceFee">
          <el-input-number
            v-model="form.baseServiceFee"
            :min="0"
            :step="0.5"
            :precision="2"
            style="width: 100%"
          />
          <div class="form-tip">留空则使用全局默认值 ¥5.00</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEditing ? '保存修改' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import StationStatusBadge from '@/components/StationStatusBadge.vue'
import {
  getAdminStationsApi,
  createStationApi,
  updateStationApi,
  deleteStationApi,
  startStationApi,
  stopStationApi,
  getProtocolsApi,
  emergencyStopStationApi,
} from '@/api/admin/station'
import type { ProtocolInfo } from '@/api/station'

// ── 状态 ──
const stations = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const protocols = ref<ProtocolInfo[]>([])
const formRef = ref<FormInstance>()

const defaultForm = {
  name: '',
  queueCapacity: 5,
  waitingCapacity: 3,
  chargingCapacity: 2,
  protocolIds: [] as number[],
  baseServiceFee: 5.0,
}

const form = reactive({ ...defaultForm })

const rules: FormRules = {
  name: [{ required: true, message: '请输入充电桩名称', trigger: 'blur' }],
  queueCapacity: [{ required: true, message: '请设置排队区容量', trigger: 'blur' }],
  waitingCapacity: [{ required: true, message: '请设置等待区容量', trigger: 'blur' }],
  chargingCapacity: [{ required: true, message: '请设置充电区容量', trigger: 'blur' }],
  protocolIds: [
    { required: true, message: '请至少选择一个协议', trigger: 'change' },
    { type: 'array', min: 1, message: '请至少选择一个协议', trigger: 'change' },
  ],
}

// ── 数据加载 ──
async function fetchStations() {
  loading.value = true
  try {
    const res = await getAdminStationsApi()
    const body = res.data as any
    stations.value = body.data?.stations || []
  } catch (err: any) {
    ElMessage.error('获取充电桩列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchProtocols() {
  try {
    const res = await getProtocolsApi()
    const body = res.data as any
    protocols.value = body.data || []
  } catch {
    protocols.value = [
      { id: 1, name: 'AC 7kW', powerKw: 7.0 },
      { id: 2, name: 'DC 22kW', powerKw: 22.0 },
      { id: 3, name: 'DC 50kW', powerKw: 50.0 },
      { id: 4, name: 'DC 120kW', powerKw: 120.0 },
      { id: 5, name: 'DC 250kW', powerKw: 250.0 },
    ]
  }
}

// ── 创建/编辑对话框 ──
function openCreate() {
  isEditing.value = false
  editingId.value = null
  Object.assign(form, defaultForm)
  dialogVisible.value = true
}

function openEdit(row: any) {
  isEditing.value = true
  editingId.value = row.id
  form.name = row.name
  form.queueCapacity = row.queueCapacity
  form.waitingCapacity = row.waitingCapacity
  form.chargingCapacity = row.chargingCapacity
  form.protocolIds = row.supportedProtocols?.map((p: any) => p.id) || []
  form.baseServiceFee = row.baseServiceFee ?? 5.0
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const data = {
      name: form.name,
      queueCapacity: form.queueCapacity,
      waitingCapacity: form.waitingCapacity,
      chargingCapacity: form.chargingCapacity,
      protocolIds: form.protocolIds,
      baseServiceFee: form.baseServiceFee,
    }

    if (isEditing.value && editingId.value) {
      await updateStationApi(editingId.value, data)
      ElMessage.success('充电桩配置已更新')
    } else {
      await createStationApi(data)
      ElMessage.success('充电桩创建成功')
    }
    dialogVisible.value = false
    fetchStations()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

// ── 启停 ──
async function handleToggleStatus(row: any) {
  try {
    if (row.status === 'running') {
      await ElMessageBox.confirm(
        `确定要停止「${row.name}」吗？停止后将不再接受新充电请求。`,
        '停止充电桩',
        { confirmButtonText: '确定停止', cancelButtonText: '取消', type: 'warning' },
      )
      await stopStationApi(row.id)
      ElMessage.success('充电桩已停止')
    } else {
      await startStationApi(row.id)
      ElMessage.success('充电桩已启动')
    }
    fetchStations()
  } catch (err: any) {
    if (err?.code !== 'cancel') {
      ElMessage.error(err?.response?.data?.message || '操作失败')
    }
  }
}

// ── 紧急停止 ──
async function handleEmergencyStop(row: any) {
  try {
    const res = await emergencyStopStationApi(row.id)
    const data = (res.data as any).data
    ElMessage.success(data.message || '紧急停止完成')
    fetchStations()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '操作失败')
  }
}

// ── 删除 ──
async function handleDelete(row: any) {
  try {
    await deleteStationApi(row.id)
    ElMessage.success('充电桩已删除')
    fetchStations()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '删除失败')
  }
}

onMounted(() => {
  fetchStations()
  fetchProtocols()
})
</script>

<style scoped>
.station-manage {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-header h2 {
  font-size: 22px;
  font-weight: 600;
  color: #1E293B;
  margin-bottom: 4px;
}

.page-desc {
  font-size: 14px;
  color: #64748B;
  margin: 0;
}

.table-card {
  border-radius: 10px;
}

.zone-info {
  display: flex;
  gap: 12px;
  font-size: 13px;
  font-family: 'JetBrains Mono', monospace;
  color: #475569;
}

.proto-tag {
  margin-right: 4px;
  margin-bottom: 2px;
  font-size: 11px;
}

.no-data {
  color: #94A3B8;
  font-size: 13px;
}

.form-tip {
  font-size: 12px;
  color: #94A3B8;
  margin-top: 4px;
}
</style>
