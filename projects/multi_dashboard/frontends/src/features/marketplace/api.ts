import { apiClient } from '../../lib/api-client'
import type { CreateOrderRequest, CreateOrderResponse } from './types'

const BASE = (import.meta.env.VITE_MARKETPLACE_API_URL ?? 'http://localhost:8006').replace(/\/$/, '')

const url = (path: string) => `${BASE}${path}`

export const marketplaceApi = {
  async createOrder(data: CreateOrderRequest): Promise<CreateOrderResponse> {
    const { data: resp } = await apiClient.post<CreateOrderResponse>(url('/orders'), data)
    return resp
  },
  async healthCheck(): Promise<{ ok: boolean; service: string }> {
    const { data } = await apiClient.get<{ ok: boolean; service: string }>(url('/health'))
    return data
  },
}
