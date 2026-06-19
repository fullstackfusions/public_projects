export interface Reminder {
  id: number
  message: string
  remind_at: string
  event_id: number
}

export interface Event {
  id: number
  title: string
  description?: string | null
  start_time: string
  end_time: string
  location?: string | null
  reminders: Reminder[]
}

export type EventPayload = Omit<Event, 'id' | 'reminders'>
export type EventUpdatePayload = Partial<EventPayload>

export type ReminderPayload = Omit<Reminder, 'id'>
export type ReminderUpdatePayload = Partial<ReminderPayload>
