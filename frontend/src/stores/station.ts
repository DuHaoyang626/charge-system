/**
 * 充电桩状态管理 (Pinia)
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { StationSummary, StationDetail } from '@/api/station'
import { getStationsApi, getStationDetailApi } from '@/api/station'

export const useStationStore = defineStore('station', () => {
  const stations = ref<StationSummary[]>([])
  const currentDetail = ref<StationDetail | null>(null)
  const loading = ref(false)

  async function fetchStations() {
    loading.value = true
    try {
      const res = await getStationsApi()
      const body = res.data as any
      stations.value = body.data?.stations || body?.stations || []
    } catch (err) {
      console.error('获取充电桩列表失败', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    loading.value = true
    try {
      const res = await getStationDetailApi(id)
      const body = res.data as any
      currentDetail.value = body.data
      return body.data
    } catch (err) {
      console.error('获取充电桩详情失败', err)
      return null
    } finally {
      loading.value = false
    }
  }

  return { stations, currentDetail, loading, fetchStations, fetchDetail }
})
