/** 充电会话状态映射 */
export const SESSION_STATUS: Record<string, { label: string; color: string; icon: string }> = {
  queued: { label: '排队中', color: '#2563EB', icon: 'Clock' },
  waiting: { label: '等待中', color: '#3B82F6', icon: 'Time' },
  charging: { label: '充电中', color: '#16A34A', icon: 'Lightning' },
  completed: { label: '已完成', color: '#6B7280', icon: 'CircleCheck' },
  cancelled: { label: '已取消', color: '#9CA3AF', icon: 'CircleClose' },
}

/** 充电桩状态映射 */
export const STATION_STATUS: Record<string, { label: string; color: string }> = {
  running: { label: '运行中', color: '#16A34A' },
  stopping: { label: '停止中', color: '#D97706' },
  stopped: { label: '已停止', color: '#6B7280' },
  error: { label: '异常', color: '#DC2626' },
}

/** 支付状态映射 */
export const PAYMENT_STATUS: Record<string, { label: string; color: string }> = {
  unpaid: { label: '未支付', color: '#D97706' },
  paid: { label: '已支付', color: '#15803D' },
}

/** 轮询间隔 (ms) — 从环境变量读取，可在 .env 中配置 */
export const POLLING_INTERVAL = Number(import.meta.env.VITE_POLLING_INTERVAL) || 3000

/** 轮询最大退避间隔 (ms) */
export const POLLING_MAX_BACKOFF = 30000

/** 充电确认倒计时 (秒) */
export const CONFIRM_TIMEOUT = 60

/** 三区名称 */
export const ZONE_LABELS: Record<string, string> = {
  queue: '排队区',
  waiting: '等待区',
  charging: '充电区',
}
