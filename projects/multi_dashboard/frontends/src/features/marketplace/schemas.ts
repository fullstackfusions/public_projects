import { z } from 'zod'

export const CreateOrderSchema = z.object({
  user_id: z.string().min(1, 'User ID is required'),
  amount_cents: z.number().int().positive('Amount must be a positive integer (cents)'),
})

export const OrderResponseSchema = z.object({
  order_id: z.string(),
  status: z.string(),
})

export type CreateOrderFormValues = z.infer<typeof CreateOrderSchema>
