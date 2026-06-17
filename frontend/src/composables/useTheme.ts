/**
 * 主题切换 composable
 * 支持明亮 / 暗色模式，并将选择持久化到 localStorage
 */

import { ref, watch } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'app-theme'

/** 当前主题（全局单例） */
const currentTheme = ref<Theme>('light')

/** 是否暗色模式 */
const isDark = ref(false)

/** 初始化主题 — 从 localStorage 读取或跟随系统 */
function initTheme() {
  const saved = localStorage.getItem(STORAGE_KEY) as Theme | null
  if (saved === 'light' || saved === 'dark') {
    currentTheme.value = saved
  } else {
    // 跟随系统
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    currentTheme.value = prefersDark ? 'dark' : 'light'
  }
  applyTheme(currentTheme.value)
}

/** 应用主题到 document */
function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme)
  currentTheme.value = theme
  isDark.value = theme === 'dark'
  localStorage.setItem(STORAGE_KEY, theme)
}

/** 切换主题 */
function toggleTheme() {
  const next = currentTheme.value === 'light' ? 'dark' : 'light'
  applyTheme(next)
}

/** 设置指定主题 */
function setTheme(theme: Theme) {
  applyTheme(theme)
}

// 首次导入时自动初始化
initTheme()

// 监控系统主题变化
if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    // 仅在用户没有手动设置过主题时跟随系统
    if (!localStorage.getItem(STORAGE_KEY)) {
      applyTheme(e.matches ? 'dark' : 'light')
    }
  })
}

export function useTheme() {
  return {
    currentTheme,
    isDark,
    toggleTheme,
    setTheme,
    initTheme,
  }
}
