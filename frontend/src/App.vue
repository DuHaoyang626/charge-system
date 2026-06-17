<template>
  <div class="app-root" :data-theme="theme">
    <router-view v-slot="{ Component }">
      <transition name="page-fade-slide" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '@/composables/useTheme'

const { currentTheme } = useTheme()
const theme = computed(() => currentTheme.value)
</script>

<style>
/* 全局重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: 'Inter Variable', -apple-system, BlinkMacSystemFont, 'Segoe UI',
    'PingFang SC', 'Microsoft YaHei', sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  background: var(--gradient-bg);
  background-attachment: fixed;
}

a {
  color: var(--color-primary);
  text-decoration: none;
}

a:hover {
  color: var(--color-primary-light);
}

/* Element Plus 覆盖 — 全局使用主题变量 */
.el-card {
  --el-card-padding: 20px;
  --el-card-border-radius: var(--radius-md);
  --el-card-border-color: var(--border-color);
  --el-card-bg-color: var(--bg-card);
  transition: all 0.3s ease;
}

.el-button--primary {
  --el-button-bg-color: var(--color-primary) !important;
  --el-button-border-color: var(--color-primary) !important;
  --el-button-hover-bg-color: var(--color-primary-light) !important;
  --el-button-hover-border-color: var(--color-primary-light) !important;
  --el-button-active-bg-color: var(--color-primary-dark) !important;
}

.el-menu--horizontal {
  --el-menu-bg-color: transparent !important;
}

.el-dialog {
  --el-dialog-bg-color: var(--bg-card);
  backdrop-filter: var(--glass-blur-lg);
  -webkit-backdrop-filter: var(--glass-blur-lg);
  border: var(--glass-border);
  border-radius: var(--radius-lg);
}

.el-message-box {
  --el-messagebox-bg-color: var(--bg-glass-strong);
  backdrop-filter: var(--glass-blur);
  border: var(--glass-border);
}

.el-table {
  --el-table-bg-color: transparent !important;
  --el-table-tr-bg-color: transparent !important;
  --el-table-header-bg-color: var(--bg-tertiary) !important;
  --el-table-row-hover-bg-color: var(--color-primary-bg) !important;
  --el-table-border-color: var(--border-light) !important;
  --el-table-text-color: var(--text-primary) !important;
  --el-table-header-text-color: var(--text-secondary) !important;
}

.el-pagination {
  --el-pagination-button-color: var(--text-secondary);
  --el-pagination-hover-color: var(--color-primary);
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--border-hover);
}
</style>
