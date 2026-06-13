<template>
  <el-tag
    :color="statusInfo.color"
    effect="plain"
    size="small"
  >
    <span class="status-dot" :style="{ backgroundColor: statusInfo.color }"></span>
    {{ statusInfo.label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STATION_STATUS } from '@/utils/constants'

const props = defineProps<{
  status: string
}>()

const statusInfo = computed(() => {
  return STATION_STATUS[props.status] || { label: props.status, color: '#9CA3AF' }
})
</script>

<style scoped>
.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
}
</style>
