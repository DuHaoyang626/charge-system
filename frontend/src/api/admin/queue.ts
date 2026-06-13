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
  targetPosition?: number
}) {
  return api.put('/admin/queues/move', data)
}
