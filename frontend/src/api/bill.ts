/**
 * 账单模块 API
 */
import api from './request'

export interface BillListParams {
  page?: number
  pageSize?: number
  paymentStatus?: string
  startDate?: string
  endDate?: string
}

export function getBillsApi(params?: BillListParams) {
  return api.get('/bills', { params })
}

export function getBillDetailApi(id: number) {
  return api.get(`/bills/${id}`)
}

export function payBillApi(id: number, paymentMethod: string) {
  return api.post(`/bills/${id}/pay`, { paymentMethod })
}
