import { useQueryClient } from '@tanstack/react-query'
import { useApiMutation, } from '../../hooks/useApiMutation'
import { useApiQuery } from '../../hooks/useApiQuery'
import { schedulerApi } from './api'
import type { EventPayload, EventUpdatePayload, ReminderPayload, ReminderUpdatePayload } from './types'

const EVENTS_KEY = ['scheduler', 'events'] as const
const REMINDERS_KEY = ['scheduler', 'reminders'] as const

export function useEvents() {
  const queryClient = useQueryClient()

  const eventsQuery = useApiQuery(EVENTS_KEY, () => schedulerApi.listEvents())

  const createEvent = useApiMutation(
    (payload: EventPayload) => schedulerApi.createEvent(payload),
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: EVENTS_KEY }) },
  )

  const updateEvent = useApiMutation(
    ({ id, payload }: { id: number; payload: EventUpdatePayload }) =>
      schedulerApi.updateEvent(id, payload),
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: EVENTS_KEY }) },
  )

  const deleteEvent = useApiMutation(
    (id: number) => schedulerApi.deleteEvent(id),
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: EVENTS_KEY }) },
  )

  return { eventsQuery, createEvent, updateEvent, deleteEvent }
}

export function useReminders() {
  const queryClient = useQueryClient()

  const remindersQuery = useApiQuery(REMINDERS_KEY, () => schedulerApi.listReminders())

  const createReminder = useApiMutation(
    (payload: ReminderPayload) => schedulerApi.createReminder(payload),
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: REMINDERS_KEY }) },
  )

  const updateReminder = useApiMutation(
    ({ id, payload }: { id: number; payload: ReminderUpdatePayload }) =>
      schedulerApi.updateReminder(id, payload),
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: REMINDERS_KEY }) },
  )

  const deleteReminder = useApiMutation(
    (id: number) => schedulerApi.deleteReminder(id),
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: REMINDERS_KEY }) },
  )

  return { remindersQuery, createReminder, updateReminder, deleteReminder }
}
