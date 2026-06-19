import { z } from 'zod'

export const AgentStepSchema = z.object({
  agent: z.string(),
  action: z.string(),
  detail: z.string().nullable(),
  timestamp: z.string(),
})

export const MessageResponseSchema = z.object({
  msg_id: z.string(),
  conversation_id: z.string(),
  status: z.enum(['processing', 'complete', 'error']),
  timestamp: z.string(),
})

export const MessageStatusResponseSchema = z.object({
  msg_id: z.string(),
  conversation_id: z.string(),
  status: z.enum(['processing', 'complete', 'error']),
  steps: z.array(AgentStepSchema),
  result: z.string().nullable(),
  error: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
