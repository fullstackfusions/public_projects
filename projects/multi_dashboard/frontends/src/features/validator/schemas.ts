import { z } from 'zod'

export const StreamEventSchema = z.object({
  type: z.string(),
  data: z.unknown(),
})

export const ValidationTaskSchema = z.object({
  change_request_id: z.string(),
  change_description: z.string(),
  change_status: z.string(),
  path: z.string(),
  devices: z.array(z.unknown()),
})

export const PaginatedTasksSchema = z.object({
  tasks: z.array(ValidationTaskSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
})
