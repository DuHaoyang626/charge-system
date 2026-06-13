/**
 * 管理端 — 充电桩管理 API
 */
import api from '@/api/request'

export interface CreateStationRequest {
  name: string
  queueCapacity: number
  waitingCapacity: number
  chargingCapacity: number
  protocolIds: number[]
  baseServiceFee?: number | null
}

export interface UpdateStationRequest {
  name?: string
  queueCapacity?: number
  waitingCapacity?: number
  chargingCapacity?: number
  protocolIds?: number[]
  baseServiceFee?: number | null
}

/** 获取所有充电桩列表 */
export function getAdminStationsApi() {
  return api.get('/stations')
}

/** 创建充电桩 */
export function createStationApi(data: CreateStationRequest) {
  return api.post('/admin/stations', data)
}

/** 修改充电桩 */
export function updateStationApi(id: number, data: UpdateStationRequest) {
  return api.put(`/admin/stations/${id}`, data)
}

/** 删除充电桩 */
export function deleteStationApi(id: number) {
  return api.delete(`/admin/stations/${id}`)
}

/** 启动充电桩 */
export function startStationApi(id: number) {
  return api.post(`/admin/stations/${id}/start`)
}

/** 正常停止充电桩 */
export function stopStationApi(id: number) {
  return api.post(`/admin/stations/${id}/stop`)
}

/** 获取所有协议 */
export function getProtocolsApi() {
  return api.get('/protocols')
}
