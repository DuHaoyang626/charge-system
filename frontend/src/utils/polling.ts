/**
 * 轮询工具 — 支持指数退避
 */

import { POLLING_INTERVAL, POLLING_MAX_BACKOFF } from './constants'

export interface PollingOptions {
  interval?: number
  maxBackoff?: number
  onTick: () => Promise<boolean> // 返回 true 停止轮询
  onError?: (err: unknown) => void
}

/**
 * 创建带指数退避的轮询
 * 返回 stop 函数
 */
export function createPolling(options: PollingOptions): () => void {
  let currentInterval = options.interval ?? POLLING_INTERVAL
  const maxBackoff = options.maxBackoff ?? POLLING_MAX_BACKOFF
  let timer: ReturnType<typeof setTimeout> | null = null
  let stopped = false

  const tick = async () => {
    if (stopped) return
    try {
      const shouldStop = await options.onTick()
      if (shouldStop) {
        stopped = true
        return
      }
      currentInterval = options.interval ?? POLLING_INTERVAL // 成功后重置间隔
    } catch (err) {
      options.onError?.(err)
      currentInterval = Math.min(currentInterval * 1.5, maxBackoff) // 失败后退避
    }
    if (!stopped) {
      timer = setTimeout(tick, currentInterval)
    }
  }

  tick()

  return () => {
    stopped = true
    if (timer) clearTimeout(timer)
  }
}
