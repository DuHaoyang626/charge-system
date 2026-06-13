<template>
  <el-tag
    effect="plain"
    size="small"
    round
    class="status-tag"
    :style="{ borderLeftColor: statusInfo.color }"
  >
    <span class="status-dot" :style="{ backgroundColor: statusInfo.color }"></span>
    {{ statusInfo.label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SESSION_STATUS } from '@/utils/constants'

const props = defineProps<{
  status: string
}>()

const statusInfo = computed(() => {
  return SESSION_STATUS[props.status] || { label: props.status, color: '#9CA3AF' }
})
</script>

<style scoped>
.status-tag {
  border-left: 3px solid;
  border-radius: 4px;
  color: #1A1A1A !important;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-left-width: 3px;
  padding-left: 6px;
  font-weight: 500;
}

.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
}
</style>
