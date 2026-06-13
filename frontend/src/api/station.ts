/**
 * 充电桩模块 API
 */
import api from './request'

export interface StationSummary {
  id: number
  name: string
  status: string
  queueCount: number
  waitingCount: number
  chargingCount: number
  queueCapacity: number
  waitingCapacity: number
  chargingCapacity: number
  supportedProtocols: ProtocolInfo[]
  estimatedWaitMinutes: number
}

export interface ProtocolInfo {
  id: number
  name: string
  powerKw: number
}

export interface ZoneSession {
  sessionId: number
  licensePlate: string
  position: number
  requestedEnergyKwh?: number
  supportedProtocols?: ProtocolInfo[]
  status: string
  estimatedWaitMinutes?: number
  chargedEnergyKwh?: number
  targetEnergyKwh?: number
  protocol?: ProtocolInfo | null
  progress?: number
  estimatedEndTime?: string | null
}

export interface StationDetail {
  id: number
  name: string
  status: string
  queueCapacity: number
  waitingCapacity: number
  chargingCapacity: number
  queueCount: number
  waitingCount: number
  chargingCount: number
  queueList: ZoneSession[]
  waitingList: ZoneSession[]
  chargingList: ZoneSession[]
  supportedProtocols: ProtocolInfo[]
}

/** 获取所有充电桩列表 */
export function getStationsApi() {
  return api.get('/stations')
}

/** 获取充电桩详情 */
export function getStationDetailApi(id: number) {
  return api.get(`/stations/${id}`)
}
