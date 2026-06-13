/**
 * 管理端 — 账单管理 API
 */
import api from '../request'

export function getAdminBillsApi(params?: Record<string, any>) {
  return api.get('/admin/bills', { params })
}

export function getAdminBillDetailApi(id: number) {
  return api.get(`/admin/bills/${id}`)
}
