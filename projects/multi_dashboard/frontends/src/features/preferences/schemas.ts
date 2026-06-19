import { z } from 'zod'

export const ChannelSchema = z.enum(['email', 'push', 'whatsapp'])

export const UserPreferenceSchema = z.object({
  id: z.number(),
  user_id: z.string(),
  email: z.string().email().nullable(),
  phone: z.string().nullable(),
  ntfy_topic: z.string().nullable(),
  enabled_channels: z.array(ChannelSchema),
  created_at: z.string(),
  updated_at: z.string(),
})

export const UpdatePreferenceSchema = z.object({
  email: z.string().email('Must be a valid email').nullable().optional(),
  phone: z.string().nullable().optional(),
  ntfy_topic: z.string().nullable().optional(),
  enabled_channels: z.array(ChannelSchema).optional(),
})

export type Channel = z.infer<typeof ChannelSchema>
export type UserPreference = z.infer<typeof UserPreferenceSchema>
export type UpdatePreference = z.infer<typeof UpdatePreferenceSchema>
