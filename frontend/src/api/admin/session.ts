/**
 * 管理端 — 会话管理 API
 */
import api from '../request'

export function getAdminSessionsApi(params?: Record<string, any>) {
  return api.get('/admin/sessions', { params })
}

export function getAdminSessionDetailApi(id: number) {
  return api.get(`/admin/sessions/${id}`)
}
