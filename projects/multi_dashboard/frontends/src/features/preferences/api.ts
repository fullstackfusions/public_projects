import { apiClient } from '../../lib/api-client'
import type { UserPreference, UpdatePreference } from './types'

const BASE = '/notification-api/preferences'

export async function getMyPreferences(): Promise<UserPreference> {
  const { data } = await apiClient.get<UserPreference>(`${BASE}/me`)
  return data
}

export async function updateMyPreferences(payload: UpdatePreference): Promise<UserPreference> {
  const { data } = await apiClient.put<UserPreference>(`${BASE}/me`, payload)
  return data
}
