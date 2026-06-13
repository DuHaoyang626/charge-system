<template>
  <el-tag
    :color="statusInfo.color"
    effect="dark"
    size="small"
    round
  >
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
