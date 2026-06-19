import { format, parseISO } from "date-fns";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { schedulerApi } from "../../api/scheduler";
import type { Event, Reminder } from "./types";

interface ReminderFormState {
  id: number | null;
  event_id: string;
  message: string;
  remind_at: string;
}

interface ReminderWithEventTitle extends Reminder {
  eventTitle: string;
}

function toDateTimeLocal(date: Date): string {
  const timezoneOffset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - timezoneOffset).toISOString().slice(0, 16);
}

function toDateTimeLocalFromIso(iso: string): string {
  return toDateTimeLocal(new Date(iso));
}

function buildDefaultReminderForm(eventId: string): ReminderFormState {
  return {
    id: null,
    event_id: eventId,
    message: "",
    remind_at: "",
  };
}

async function safeExecute<T>(
  action: () => Promise<T>,
  onError: (message: string) => void
): Promise<T | undefined> {
  try {
    return await action();
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Something went wrong";
    onError(message);
    return undefined;
  }
}

export function RemindersPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<Event[]>([]);
  const [reminderForm, setReminderForm] = useState<ReminderFormState>(
    buildDefaultReminderForm("")
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reminderSubmitting, setReminderSubmitting] = useState(false);

  const reminders: ReminderWithEventTitle[] = useMemo(
    () =>
      events
        .flatMap((event) =>
          event.reminders.map((reminder) => ({
            ...reminder,
            eventTitle: event.title,
          }))
        )
        .sort(
          (a, b) =>
            new Date(a.remind_at).getTime() - new Date(b.remind_at).getTime()
        ),
    [events]
  );

  useEffect(() => {
    void loadEvents();
  }, []);

  useEffect(() => {
    if (
      reminderForm.id === null &&
      events.length > 0 &&
      !reminderForm.event_id
    ) {
      setReminderForm((prev) => ({
        ...prev,
        event_id: String(events[0].id),
      }));
    }
  }, [events, reminderForm.id, reminderForm.event_id]);

  const inputClass =
    "rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm shadow-sm transition focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/40";
  const primaryButtonClass =
    "inline-flex items-center justify-center rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand/40 disabled:cursor-not-allowed disabled:opacity-70";
  const secondaryButtonClass =
    "inline-flex items-center justify-center rounded-xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-300";
  const dangerButtonClass =
    "inline-flex items-center justify-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-500 focus:outline-none focus:ring-2 focus:ring-rose-300";

  async function loadEvents(silent = false) {
    const data = await safeExecute(
      async () => schedulerApi.listEvents(),
      setErrorMessage
    );
    if (data) {
      setEvents(data);
      setErrorMessage(null);
    }
  }

  function resetReminderForm(eventId = reminderForm.event_id) {
    setReminderForm(buildDefaultReminderForm(eventId));
  }

  async function handleSubmitReminder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    if (!reminderForm.event_id) {
      setErrorMessage("Select an event for the reminder");
      return;
    }

    if (!reminderForm.message.trim()) {
      setErrorMessage("Reminder message is required");
      return;
    }

    if (!reminderForm.remind_at) {
      setErrorMessage("Reminder date and time is required");
      return;
    }

    const payload = {
      event_id: Number(reminderForm.event_id),
      message: reminderForm.message.trim(),
      remind_at: new Date(reminderForm.remind_at).toISOString(),
    };

    setReminderSubmitting(true);
    if (reminderForm.id) {
      await safeExecute(
        () => schedulerApi.updateReminder(reminderForm.id!, payload),
        setErrorMessage
      );
    } else {
      await safeExecute(
        () => schedulerApi.createReminder(payload),
        setErrorMessage
      );
    }
    setReminderSubmitting(false);
    await loadEvents(true);
    resetReminderForm(String(payload.event_id));
  }

  async function handleDeleteReminder(item: ReminderWithEventTitle) {
    const confirmed = window.confirm(
      `Delete reminder for event "${item.eventTitle}"?`
    );
    if (!confirmed) {
      return;
    }
    await safeExecute(
      () => schedulerApi.deleteReminder(item.id),
      setErrorMessage
    );
    await loadEvents(true);
    resetReminderForm(reminderForm.event_id);
  }

  function handleEditReminder(item: ReminderWithEventTitle) {
    setReminderForm({
      id: item.id,
      event_id: String(item.event_id),
      message: item.message,
      remind_at: toDateTimeLocalFromIso(item.remind_at),
    });
  }

  return (
    <div className="flex flex-col gap-6 h-full">
      {errorMessage && (
        <div className="rounded-xl border border-rose-200 bg-rose-100 px-4 py-3 text-sm text-rose-700 shadow-sm">
          {errorMessage}
        </div>
      )}

      <div className="grid gap-7 xl:grid-cols-[minmax(320px,380px)_1fr] flex-1">
        <section className="space-y-6 rounded-2xl bg-white p-6 shadow-card">
          <h2 className="text-xl font-semibold text-slate-900">
            {reminderForm.id ? "Edit Reminder" : "Create Reminder"}
          </h2>
          {events.length === 0 ? (
            <div className="flex flex-col gap-4">
              <p className="text-sm text-slate-600">
                You need to create an event before you can add a reminder.
              </p>
              <button
                type="button"
                onClick={() => navigate("/scheduler")}
                className={primaryButtonClass}
              >
                Go to Scheduler
              </button>
            </div>
          ) : (
            <form
              onSubmit={handleSubmitReminder}
              className="flex flex-col gap-4"
            >
              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Event
                <select
                  value={reminderForm.event_id}
                  onChange={(e) =>
                    setReminderForm((prev) => ({
                      ...prev,
                      event_id: e.target.value,
                    }))
                  }
                  className={inputClass}
                >
                  <option value="">Select event</option>
                  {events.map((event) => (
                    <option key={event.id} value={event.id}>
                      {event.title}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Message
                <input
                  type="text"
                  value={reminderForm.message}
                  onChange={(e) =>
                    setReminderForm((prev) => ({
                      ...prev,
                      message: e.target.value,
                    }))
                  }
                  className={inputClass}
                  required
                />
              </label>

              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Remind At
                <input
                  type="datetime-local"
                  value={reminderForm.remind_at}
                  onChange={(e) =>
                    setReminderForm((prev) => ({
                      ...prev,
                      remind_at: e.target.value,
                    }))
                  }
                  className={inputClass}
                  required
                />
              </label>

              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  className={primaryButtonClass}
                  disabled={reminderSubmitting}
                >
                  {reminderForm.id ? "Update Reminder" : "Add Reminder"}
                </button>
                {reminderForm.id && (
                  <button
                    type="button"
                    className={secondaryButtonClass}
                    onClick={() => resetReminderForm(reminderForm.event_id)}
                  >
                    Cancel
                  </button>
                )}
              </div>
            </form>
          )}
        </section>

        <section className="space-y-4 rounded-2xl bg-white p-6 shadow-card">
          <h2 className="text-xl font-semibold text-slate-900">Reminders</h2>
          {reminders.length === 0 ? (
            <p className="text-sm text-slate-500">No reminders set.</p>
          ) : (
            <ul className="flex flex-col gap-4">
              {reminders.map((item) => (
                <li
                  key={item.id}
                  className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="space-y-1 text-sm text-slate-600">
                    <strong className="block text-base font-semibold text-slate-900">
                      {item.message}
                    </strong>
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Event: {item.eventTitle}
                    </div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      At: {format(parseISO(item.remind_at), "Pp")}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    <button
                      type="button"
                      className={secondaryButtonClass}
                      onClick={() => handleEditReminder(item)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className={dangerButtonClass}
                      onClick={() => handleDeleteReminder(item)}
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
