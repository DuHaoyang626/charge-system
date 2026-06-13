/**
 * 格式化金额 (元)
 * 使用等宽字体友好格式，保留两位小数
 */
export function formatFee(fee: number): string {
  return `¥${fee.toFixed(2)}`
}

/**
 * 格式化百分比
 */
export function formatPercent(value: number): string {
  return `${Math.round(value)}%`
}

/**
 * 格式化时间戳为本地时间字符串
 * ISO 8601 → 本地显示
 */
export function formatTime(isoString: string | null | undefined): string {
  if (!isoString) return '--'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * 格式化充电时长 (秒 → HH:mm:ss)
 */
export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) {
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

/**
 * 脱敏车牌号（保留前1后1，中间用*代替）
 */
export function maskLicensePlate(plate: string): string {
  if (!plate || plate.length < 3) return plate
  return plate[0] + '*'.repeat(plate.length - 2) + plate[plate.length - 1]
}
