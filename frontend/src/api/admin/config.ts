/**
 * 管理端 — 配置管理 API
 */
import api from '../request'

export function getAdminConfigApi() {
  return api.get('/admin/config')
}

export function updateAdminConfigApi(data: Record<string, any>) {
  return api.put('/admin/config', data)
}
