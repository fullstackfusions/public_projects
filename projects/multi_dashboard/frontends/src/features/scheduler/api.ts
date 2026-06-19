import { apiClient } from "../../lib/api-client";
import type {
  Event,
  EventPayload,
  EventUpdatePayload,
  Reminder,
  ReminderPayload,
  ReminderUpdatePayload,
} from "./types";

const BASE = (
  import.meta.env.VITE_SCHEDULER_API_BASE ?? "/scheduler-api"
).replace(/\/$/, "");

const url = (path: string) => `${BASE}${path}`;

interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export const schedulerApi = {
  async listEvents(): Promise<Event[]> {
    const { data } = await apiClient.get<Page<Event> | Event[]>(url("/events"));
    return Array.isArray(data) ? data : data.items;
  },
  async createEvent(payload: EventPayload): Promise<Event> {
    const { data } = await apiClient.post<Event>(url("/events"), payload);
    return data;
  },
  async updateEvent(
    eventId: number,
    payload: EventUpdatePayload,
  ): Promise<Event> {
    const { data } = await apiClient.put<Event>(
      url(`/events/${eventId}`),
      payload,
    );
    return data;
  },
  async deleteEvent(eventId: number): Promise<void> {
    await apiClient.delete(url(`/events/${eventId}`));
  },
  async listReminders(): Promise<Reminder[]> {
    const { data } = await apiClient.get<Page<Reminder> | Reminder[]>(
      url("/reminders"),
    );
    return Array.isArray(data) ? data : data.items;
  },
  async createReminder(payload: ReminderPayload): Promise<Reminder> {
    const { data } = await apiClient.post<Reminder>(url("/reminders"), payload);
    return data;
  },
  async updateReminder(
    reminderId: number,
    payload: ReminderUpdatePayload,
  ): Promise<Reminder> {
    const { data } = await apiClient.put<Reminder>(
      url(`/reminders/${reminderId}`),
      payload,
    );
    return data;
  },
  async deleteReminder(reminderId: number): Promise<void> {
    await apiClient.delete(url(`/reminders/${reminderId}`));
  },
};
