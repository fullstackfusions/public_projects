import { z } from 'zod'

export const TodoSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string().nullable(),
  completed: z.boolean(),
  due_date: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})

export const CreateTodoSchema = z.object({
  title: z.string().min(1, 'Title is required').max(200, 'Title is too long'),
  description: z.string().optional(),
})

export const UpdateTodoSchema = CreateTodoSchema.partial().extend({
  completed: z.boolean().optional(),
})

export type CreateTodoFormValues = z.infer<typeof CreateTodoSchema>
export type UpdateTodoFormValues = z.infer<typeof UpdateTodoSchema>
