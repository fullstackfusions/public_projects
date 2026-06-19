import { apiClient } from '../../lib/api-client'
import type { PaginatedTasksResponse, SortOrder, StreamEvent, TaskFilters } from './types'

const BASE = (import.meta.env.VITE_VALIDATOR_API_URL ?? 'http://localhost:8002').replace(/\/$/, '')

const url = (path: string) => `${BASE}${path}`

export interface StreamCallbacks {
  onEvent?: (event: StreamEvent) => void
  onError?: (error: Error) => void
  onComplete?: () => void
}

async function processSSEStream(response: Response, callbacks: StreamCallbacks): Promise<void> {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('Response body is not readable')

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        callbacks.onComplete?.()
        break
      }
      buffer += decoder.decode(value, { stream: true })
      const messages = buffer.split('\n\n')
      buffer = messages.pop() ?? ''
      for (const message of messages) {
        if (!message.trim().startsWith('data: ')) continue
        try {
          const event = JSON.parse(message.slice(6)) as StreamEvent
          callbacks.onEvent?.(event)
          if (event.type === 'error') {
            callbacks.onError?.(new Error((event.data as { error: string }).error))
          }
        } catch (e) {
          console.error('SSE frame parse failure:', e)
        }
      }
    }
  } catch (error) {
    callbacks.onError?.(error instanceof Error ? error : new Error(String(error)))
  }
}

function sseHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    Accept: 'text/event-stream',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function streamValidationResult(
  changeRequestId: string,
  deviceId: string,
  callbacks: StreamCallbacks,
): Promise<void> {
  try {
    const response = await fetch(url(`/${changeRequestId}/${deviceId}/stream`), {
      method: 'GET',
      headers: sseHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    await processSSEStream(response, callbacks)
  } catch (error) {
    callbacks.onError?.(error instanceof Error ? error : new Error(String(error)))
  }
}

export async function fetchNextChunk(
  changeRequestId: string,
  deviceId: string,
  offset: number,
  side: 'pre' | 'post',
  commandIndex: number,
  callbacks: StreamCallbacks,
): Promise<void> {
  const params = new URLSearchParams({
    offset: offset.toString(),
    side,
    command_index: commandIndex.toString(),
  })
  try {
    const response = await fetch(url(`/${changeRequestId}/${deviceId}/stream?${params}`), {
      method: 'GET',
      headers: sseHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    await processSSEStream(response, callbacks)
  } catch (error) {
    callbacks.onError?.(error instanceof Error ? error : new Error(String(error)))
  }
}

export interface FetchTasksParams {
  page?: number
  pageSize?: number
  sortBy?: string | null
  sortOrder?: SortOrder
  filters?: Partial<TaskFilters>
}

export async function fetchValidationTasks(params: FetchTasksParams = {}): Promise<PaginatedTasksResponse> {
  const { page = 1, pageSize = 5, sortBy, sortOrder, filters } = params
  const query: Record<string, string> = {
    page: page.toString(),
    page_size: pageSize.toString(),
  }
  if (sortBy && sortOrder) {
    query.sort_by = sortBy
    query.sort_order = sortOrder
  }
  if (filters) {
    if (filters.change_request_id) query.change_request_id = filters.change_request_id
    if (filters.change_description) query.change_description = filters.change_description
    if (filters.change_status) query.change_status = filters.change_status
    if (filters.path) query.path = filters.path
  }
  const { data } = await apiClient.get<PaginatedTasksResponse>(url('/tasks'), { params: query })
  return data
}

export async function clearTasksCache(): Promise<void> {
  await apiClient.delete(url('/tasks/cache'))
}
