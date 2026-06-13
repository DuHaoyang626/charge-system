/**
 * 管理端 — 报表统计 API
 */
import api from '../request'

export function getChargingVolumeApi(params?: Record<string, any>) {
  return api.get('/admin/reports/charging-volume', { params })
}

export function getRevenueApi(params?: Record<string, any>) {
  return api.get('/admin/reports/revenue', { params })
}

export function getUtilizationApi() {
  return api.get('/admin/reports/utilization')
}
