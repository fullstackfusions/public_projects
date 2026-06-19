import { apiClient } from '../../lib/api-client'
import type { MessageResponse, MessageStatusResponse } from './types'

const BASE = (import.meta.env.VITE_AGENTIC_CHAT_API_URL ?? 'http://localhost:8010').replace(/\/$/, '')

const url = (path: string) => `${BASE}${path}`

export async function postMessage(message: string, conversationId?: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(url('/message'), {
    message,
    conversation_id: conversationId,
  })
  return data
}

export async function getMessageStatus(msgId: string): Promise<MessageStatusResponse> {
  const { data } = await apiClient.get<MessageStatusResponse>(url(`/message/${msgId}`))
  return data
}
