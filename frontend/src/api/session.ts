/**
 * 充电会话模块 API
 */
import api from './request'

export interface CreateSessionRequest {
  requestedEnergyKwh: number
  protocolIds: number[]
}

export interface CreateSessionResponse {
  sessionId: number
  status: string
  zone: string
  queuePosition: number
  station: { id: number; name: string }
  requestedEnergyKwh: number
  estimatedWaitMinutes: number
  createdAt: string
}

export function createSessionApi(data: CreateSessionRequest) {
  return api.post('/sessions', data)
}

export function getSessionDetailApi(id: number) {
  return api.get(`/sessions/${id}`)
}

export function getSwitchOptionsApi(id: number) {
  return api.get(`/sessions/${id}/switch-options`)
}

export function switchStationApi(id: number, targetStationId: number) {
  return api.post(`/sessions/${id}/switch-station`, { targetStationId })
}

export function cancelSessionApi(id: number) {
  return api.post(`/sessions/${id}/cancel`)
}
