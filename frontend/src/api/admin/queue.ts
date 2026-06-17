/**
 * 管理端队列 API
 */
import api from '../request'

export function getAdminQueuesApi() {
  return api.get('/admin/queues')
}

export function reorderQueueApi(data: {
  stationId: number
  zone: string
  sessionId: number
  newPosition: number
}) {
  return api.put('/admin/queues/reorder', data)
}

export function moveSessionApi(data: {
  sessionId: number
  targetStationId: number
  targetZone: string
  targetPosition?: number
}) {
  return api.put('/admin/queues/move', data)
}

/** 调度日志查询参数 */
export interface ScheduleLogsParams {
  page?: number
  pageSize?: number
  sessionId?: number
}

/** 获取调度日志 */
export function getScheduleLogsApi(params?: ScheduleLogsParams) {
  return api.get('/admin/queues/logs', { params })
}
