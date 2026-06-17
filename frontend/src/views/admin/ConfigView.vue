<template>
  <div class="config-view">
    <div class="page-header">
      <div>
        <h2>⚙️ 系统配置</h2>
        <p class="page-desc">调度策略、电价和服务费配置</p>
      </div>
    </div>

    <div v-loading="loading">
      <template v-if="config">
        <!-- 全局配置 -->
        <div class="glass-card section-card">
          <div class="card-title">⚙️ 全局配置</div>
          <el-form label-position="top" size="small">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="调度算法">
                  <el-select v-model="editSchedulingAlgorithm" style="width:100%">
                    <el-option value="shortest_time_single" label="单次调度最短时长" />
                    <el-option value="batch_shortest" label="批量调度最短总时长（匈牙利算法）" />
                    <el-option value="priority" label="优先级调度（VIP 优先）" />
                    <el-option value="time_order" label="时间顺序调度（FIFO）" />
                    <el-option value="fault_recovery" label="充电中故障恢复优先" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="基础服务费（元）">
                  <el-input-number v-model="editBaseServiceFee" :min="0" :max="100" :step="0.5"
                    :precision="2" style="width:160px" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>

        <!-- 电价时段 -->
        <div class="glass-card section-card">
          <div class="card-title">⚡ 电价时段</div>
          <el-alert v-if="priceConflictError" type="warning" :title="priceConflictError" closable
            @close="priceConflictError = ''" show-icon style="margin-bottom:12px" />
          <el-table :data="editPrices" size="small" stripe>
            <el-table-column label="时段名称" width="130">
              <template #default="{ row, $index }">
                <el-input v-model="row.periodName" size="small" placeholder="如：峰时" />
              </template>
            </el-table-column>
            <el-table-column label="开始时间" width="140">
              <template #default="{ row, $index }">
                <el-time-picker v-model="row.startObj" format="HH:mm" value-format="HH:mm"
                  style="width:110px" size="small" placeholder="08:00" />
              </template>
            </el-table-column>
            <el-table-column label="结束时间" width="140">
              <template #default="{ row, $index }">
                <el-time-picker v-model="row.endObj" format="HH:mm" value-format="HH:mm"
                  style="width:110px" size="small" placeholder="11:00" />
              </template>
            </el-table-column>
            <el-table-column label="电价 (元/kWh)" width="150">
              <template #default="{ row, $index }">
                <el-input-number v-model="row.pricePerKwh" :min="0" :max="10" :step="0.1"
                  :precision="2" size="small" style="width:120px" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ $index }">
                <button class="btn-glass btn-glass-sm btn-glass-danger" style="padding:2px 8px;font-size:11px;min-height:28px;" @click="removePrice($index)">删除</button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top:8px">
            <button class="btn-glass btn-glass-sm" @click="addPrice">+ 添加时段</button>
          </div>
        </div>

        <!-- 服务费阶梯 -->
        <div class="glass-card section-card">
          <div class="card-title">💰 服务费阶梯</div>
          <el-table :data="editTiers" size="small" stripe>
            <el-table-column label="阶梯名称" width="150">
              <template #default="{ row, $index }">
                <el-input v-model="row.tierName" size="small" placeholder="如：0-60分钟" />
              </template>
            </el-table-column>
            <el-table-column label="最小分钟" width="120">
              <template #default="{ row, $index }">
                <el-input-number v-model="row.minMinutes" :min="0" :max="9999" size="small" style="width:100px" />
              </template>
            </el-table-column>
            <el-table-column label="最大分钟" width="120">
              <template #default="{ row, $index }">
                <el-input-number v-model="row.maxMinutes" :min="0" :max="99999" size="small"
                  style="width:100px" :placeholder="'∞'" :controls="false" />
              </template>
            </el-table-column>
            <el-table-column label="费率 (元/分钟)" width="150">
              <template #default="{ row, $index }">
                <el-input-number v-model="row.ratePerMinute" :min="0" :max="10" :step="0.01"
                  :precision="3" size="small" style="width:120px" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ $index }">
                <button class="btn-glass btn-glass-sm btn-glass-danger" style="padding:2px 8px;font-size:11px;min-height:28px;" @click="removeTier($index)">删除</button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top:8px">
            <button class="btn-glass btn-glass-sm" @click="addTier">+ 添加阶梯</button>
          </div>
        </div>

        <div class="save-bar">
          <button class="btn-glass btn-glass-primary" :disabled="saving" @click="handleSave">
            {{ saving ? '⏳ 保存中...' : '💾 保存配置' }}
          </button>
          <button class="btn-glass" @click="fetchConfig">🔄 重置</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdminConfigApi, updateAdminConfigApi } from '@/api/admin/config'

const loading = ref(true)
const saving = ref(false)
const config = ref<any>(null)
const priceConflictError = ref('')

const editSchedulingAlgorithm = ref('shortest_time_single')
const editBaseServiceFee = ref(5.0)
const editPrices = reactive<any[]>([])
const editTiers = reactive<any[]>([])

function _toMinutes(t: string): number {
  const parts = t.split(':')
  return parseInt(parts[0]) * 60 + parseInt(parts[1])
}

function _validatePricesNoConflict(prices: any[]): string | null {
  const intervals: { start: number; end: number; name: string }[] = []
  for (const p of prices) {
    if (!p.start || !p.end) continue
    const start = _toMinutes(p.start)
    let end = _toMinutes(p.end)
    const name = p.periodName || ''
    if (end <= start) {
      intervals.push({ start, end: 1440, name })
      intervals.push({ start: 0, end, name })
    } else {
      intervals.push({ start, end, name })
    }
  }
  intervals.sort((a, b) => a.start - b.start)
  for (let i = 0; i < intervals.length; i++) {
    for (let j = i + 1; j < intervals.length; j++) {
      if (intervals[j].start < intervals[i].end) {
        return `电价时段 "${intervals[i].name}" 与 "${intervals[j].name}" 存在时间冲突`
      }
    }
  }
  return null
}

async function fetchConfig() {
  loading.value = true
  try {
    const res = await getAdminConfigApi()
    config.value = (res.data as any).data
    const c = config.value

    editSchedulingAlgorithm.value = c.schedulingAlgorithm || 'shortest_time_single'
    editBaseServiceFee.value = c.baseServiceFee ?? 5.0

    editPrices.length = 0
    ;(c.electricityPrices || []).forEach((p: any) => {
      editPrices.push({
        periodName: p.periodName,
        start: p.start,
        end: p.end,
        pricePerKwh: p.pricePerKwh,
        startObj: p.start,
        endObj: p.end,
      })
    })

    editTiers.length = 0
    ;(c.serviceFeeTiers || []).forEach((t: any) => {
      editTiers.push({
        tierName: '',
        minMinutes: t.minMinutes,
        maxMinutes: t.maxMinutes,
        ratePerMinute: t.ratePerMinute,
      })
    })
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '加载配置失败')
  } finally { loading.value = false }
}

function addPrice() {
  editPrices.push({
    periodName: '',
    start: '00:00',
    end: '01:00',
    pricePerKwh: 0.8,
    startObj: '00:00',
    endObj: '01:00',
  })
}

function removePrice(index: number) { editPrices.splice(index, 1) }

function addTier() {
  editTiers.push({
    tierName: '',
    minMinutes: 0,
    maxMinutes: 60,
    ratePerMinute: 0.15,
  })
}

function removeTier(index: number) { editTiers.splice(index, 1) }

async function handleSave() {
  const pricesToCheck = editPrices.map((p: any) => ({
    periodName: p.periodName,
    start: p.startObj || p.start,
    end: p.endObj || p.end,
  }))
  const conflict = _validatePricesNoConflict(pricesToCheck)
  if (conflict) {
    priceConflictError.value = conflict
    ElMessage.warning(conflict)
    return
  }
  priceConflictError.value = ''

  saving.value = true
  try {
    const data: Record<string, any> = {}
    data.schedulingAlgorithm = editSchedulingAlgorithm.value
    data.baseServiceFee = editBaseServiceFee.value
    data.electricityPrices = editPrices.map((p: any) => ({
      periodName: p.periodName,
      start: p.startObj || p.start,
      end: p.endObj || p.end,
      pricePerKwh: p.pricePerKwh,
    }))
    data.serviceFeeTiers = editTiers.map((t: any) => ({
      tierName: t.tierName || undefined,
      minMinutes: t.minMinutes,
      maxMinutes: t.maxMinutes || null,
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
.config-view { max-width: 960px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.section-card { padding: 24px; margin-bottom: 16px; }

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.save-bar { display: flex; gap: 12px; margin-top: 8px; }
</style>
