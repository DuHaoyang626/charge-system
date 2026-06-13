<template>
  <router-view />
</template>

<script setup lang="ts">
// 根组件 — 仅作路由出口
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
  background-color: #F5F5F5;
  color: #1A1A1A;
}

a {
  color: #2563EB;
  text-decoration: none;
}

a:hover {
  color: #1E40AF;
}
</style>
