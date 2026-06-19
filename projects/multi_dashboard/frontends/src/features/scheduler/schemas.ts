import { z } from 'zod'

export const ReminderSchema = z.object({
  id: z.number(),
  message: z.string(),
  remind_at: z.string(),
  event_id: z.number(),
})

export const EventSchema = z.object({
  id: z.number(),
  title: z.string(),
  description: z.string().nullish(),
  start_time: z.string(),
  end_time: z.string(),
  location: z.string().nullish(),
  reminders: z.array(ReminderSchema),
})

export const EventFormSchema = z
  .object({
    title: z.string().min(1, 'Title is required'),
    description: z.string().optional(),
    start_time: z.string().min(1, 'Start time is required'),
    end_time: z.string().min(1, 'End time is required'),
    location: z.string().optional(),
  })
  .refine((d) => !d.start_time || !d.end_time || d.end_time > d.start_time, {
    message: 'End time must be after start time',
    path: ['end_time'],
  })

export const ReminderFormSchema = z.object({
  message: z.string().min(1, 'Message is required'),
  remind_at: z.string().min(1, 'Remind at time is required'),
  event_id: z.number({ invalid_type_error: 'Event is required' }).int().positive('Event is required'),
})

export type EventFormValues = z.infer<typeof EventFormSchema>
export type ReminderFormValues = z.infer<typeof ReminderFormSchema>
