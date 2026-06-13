/**
 * 充电会话模块 API
 */
import api from './request'

export interface CreateSessionRequest {
  requestedEnergyKwh: number
  protocolIds: number[]
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

export function confirmChargingApi(id: number, data: { action: string; protocolId?: number; requestedEnergyKwh?: number }) {
  return api.post(`/sessions/${id}/confirm-charging`, data)
}

export function updateEnergyApi(id: number, requestedEnergyKwh: number) {
  return api.put(`/sessions/${id}/energy`, { requestedEnergyKwh })
}

export function getProtocolOptionsApi(id: number) {
  return api.get(`/sessions/${id}/protocol-options`)
}

export function updateProtocolApi(id: number, protocolIds: number[]) {
  return api.put(`/sessions/${id}/protocol`, { protocolIds })
}

export function stopChargingApi(id: number) {
  return api.post(`/sessions/${id}/stop-charging`)
}
