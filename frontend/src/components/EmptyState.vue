<template>
  <div class="empty-state">
    <el-icon :size="48" color="#D1D5DB">
      <component :is="icon" />
    </el-icon>
    <p class="empty-text">{{ description }}</p>
    <el-button v-if="actionText" type="primary" @click="$emit('action')">
      {{ actionText }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon?: string
  description: string
  actionText?: string
}>()

defineEmits<{
  action: []
}>()
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  gap: 16px;
}

.empty-text {
  color: #9CA3AF;
  font-size: 14px;
}
</style>
