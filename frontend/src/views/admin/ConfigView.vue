<template>
  <div class="config-view" v-loading="loading">
    <h2>系统配置</h2>

    <template v-if="config">
      <!-- 全局配置 -->
      <el-card shadow="never" class="section-card">
        <template #header>⚙️ 全局配置</template>
        <el-form label-position="top" size="small">
          <el-row :gutter="16">
            <template v-for="(val, key) in config.globalConfigs" :key="key">
              <el-col :span="8" v-if="key === 'scheduling_algorithm'">
                <el-form-item label="调度算法">
                  <el-select v-model="editConfigs[key]" style="width:100%">
                    <el-option value="shortest_time_single" label="单次调度最短时长" />
                    <el-option value="batch_shortest" label="批量调度最短总时长（匈牙利算法）" />
                    <el-option value="priority" label="优先级调度（VIP 优先）" />
                    <el-option value="time_order" label="时间顺序调度（FIFO）" />
                    <el-option value="fault_recovery" label="充电中故障恢复优先" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8" v-else>
                <el-form-item :label="key">
                  <el-input v-model="editConfigs[key]" />
                </el-form-item>
              </el-col>
            </template>
          </el-row>
        </el-form>
      </el-card>

      <!-- 电价时段 -->
      <el-card shadow="never" class="section-card">
        <template #header>⚡ 电价时段</template>
        <el-table :data="config.electricityPrices" size="small" stripe>
          <el-table-column label="时段名称">
            <template #default="{ row, $index }">
              <el-input v-model="editPrices[$index].periodName" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="开始时间" width="120">
            <template #default="{ row, $index }">
              <el-time-picker v-model="editPrices[$index].startTimeObj" format="HH:mm" value-format="HH:mm"
                style="width:100px" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="结束时间" width="120">
            <template #default="{ row, $index }">
              <el-time-picker v-model="editPrices[$index].endTimeObj" format="HH:mm" value-format="HH:mm"
                style="width:100px" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="电价 (元/kWh)" width="150">
            <template #default="{ row, $index }">
              <el-input-number v-model="editPrices[$index].pricePerKwh" :min="0" :max="10" :step="0.1"
                :precision="2" size="small" style="width:120px" />
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 服务费阶梯 -->
      <el-card shadow="never" class="section-card">
        <template #header>💰 服务费阶梯</template>
        <el-table :data="config.serviceFeeTiers" size="small" stripe>
          <el-table-column label="阶梯名称">
            <template #default="{ row, $index }">
              <el-input v-model="editTiers[$index].tierName" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="最小分钟" width="100">
            <template #default="{ row, $index }">
              {{ row.minMinutes }}
            </template>
          </el-table-column>
          <el-table-column label="最大分钟" width="100">
            <template #default="{ row, $index }">
              {{ row.maxMinutes ?? '∞' }}
            </template>
          </el-table-column>
          <el-table-column label="费率 (元/分钟)" width="150">
            <template #default="{ row, $index }">
              <el-input-number v-model="editTiers[$index].ratePerMinute" :min="0" :max="10" :step="0.01"
                :precision="3" size="small" style="width:120px" />
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <div class="save-bar">
        <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
        <el-button @click="fetchConfig">重置</el-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdminConfigApi, updateAdminConfigApi } from '@/api/admin/config'

const loading = ref(true)
const saving = ref(false)
const config = ref<any>(null)

// 编辑态副本
const editConfigs = reactive<Record<string, string>>({})
const editPrices = reactive<any[]>([])
const editTiers = reactive<any[]>([])

async function fetchConfig() {
  loading.value = true
  try {
    const res = await getAdminConfigApi()
    config.value = (res.data as any).data

    // 填充编辑副本
    Object.assign(editConfigs, config.value.globalConfigs || {})
    editPrices.length = 0
    ;(config.value.electricityPrices || []).forEach((p: any) => {
      editPrices.push({ ...p, startTimeObj: p.startTime, endTimeObj: p.endTime })
    })
    editTiers.length = 0
    ;(config.value.serviceFeeTiers || []).forEach((t: any) => {
      editTiers.push({ ...t })
    })
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '加载配置失败')
  } finally { loading.value = false }
}

async function handleSave() {
  saving.value = true
  try {
    const data: Record<string, any> = {}

    // 全局配置
    data.globalConfigs = { ...editConfigs }

    // 电价
    data.electricityPrices = editPrices.map((p: any) => ({
      id: p.id,
      periodName: p.periodName,
      startTime: p.startTimeObj || p.startTime,
      endTime: p.endTimeObj || p.endTime,
      pricePerKwh: p.pricePerKwh,
      priority: p.priority,
    }))

    // 服务费
    data.serviceFeeTiers = editTiers.map((t: any) => ({
      id: t.id,
      tierName: t.tierName,
      ratePerMinute: t.ratePerMinute,
    }))

    await updateAdminConfigApi(data)
    ElMessage.success('配置已更新')
    fetchConfig()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '保存失败')
  } finally { saving.value = false }
}

onMounted(fetchConfig)
</script>

<style scoped>
.config-view { max-width: 900px; }
.config-view h2 { font-size: 22px; font-weight: 600; color: #1E293B; margin-bottom: 20px; }
.section-card { border-radius: 10px; margin-bottom: 16px; }
.section-card :deep(.el-card__header) { font-weight: 600; font-size: 15px; }
.save-bar { display: flex; gap: 12px; margin-top: 8px; }
</style>
