import { zodResolver } from '@hookform/resolvers/zod'
import {
  format,
  isSameDay,
  parseISO,
  set as setTime,
  startOfMonth,
} from 'date-fns'
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'

import { schedulerApi } from './api'
import { Calendar } from './components/Calendar'
import { EventFormSchema, type EventFormValues } from './schemas'
import type { Event } from './types'

function toDateTimeLocal(date: Date): string {
  const timezoneOffset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - timezoneOffset).toISOString().slice(0, 16)
}

function toDateTimeLocalFromIso(iso: string): string {
  return toDateTimeLocal(new Date(iso))
}

function buildDefaultForm(date: Date): EventFormValues {
  const start = setTime(date, { hours: 9, minutes: 0, seconds: 0, milliseconds: 0 })
  const end = setTime(date, { hours: 10, minutes: 0, seconds: 0, milliseconds: 0 })
  return {
    title: '',
    description: '',
    start_time: toDateTimeLocal(start),
    end_time: toDateTimeLocal(end),
    location: '',
  }
}

async function safeExecute<T>(
  action: () => Promise<T>,
  onError: (message: string) => void,
): Promise<T | undefined> {
  try {
    return await action()
  } catch (error) {
    onError(error instanceof Error ? error.message : 'Something went wrong')
    return undefined
  }
}

export function SchedulerPage() {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [currentMonth, setCurrentMonth] = useState<Date>(startOfMonth(new Date()))
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EventFormValues>({
    resolver: zodResolver(EventFormSchema),
    defaultValues: buildDefaultForm(new Date()),
  })

  const eventsForSelectedDate = useMemo(
    () => events.filter((e) => isSameDay(parseISO(e.start_time), selectedDate)),
    [events, selectedDate],
  )

  useEffect(() => {
    void loadEvents()
  }, [])

  useEffect(() => {
    if (editingId === null) {
      reset(buildDefaultForm(selectedDate))
    }
  }, [selectedDate, editingId, reset])

  const inputClass =
    'rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm shadow-sm transition focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/40'
  const textAreaClass = `${inputClass} min-h-[7rem]`
  const primaryBtnClass =
    'inline-flex items-center justify-center rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand/40 disabled:cursor-not-allowed disabled:opacity-70'
  const secondaryBtnClass =
    'inline-flex items-center justify-center rounded-xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-300'
  const dangerBtnClass =
    'inline-flex items-center justify-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-500 focus:outline-none focus:ring-2 focus:ring-rose-300'

  async function loadEvents(silent = false) {
    if (!silent) setLoading(true)
    const data = await safeExecute(() => schedulerApi.listEvents(), setErrorMessage)
    if (data) {
      setEvents(data)
      setErrorMessage(null)
    }
    if (!silent) setLoading(false)
  }

  function resetForm(date = selectedDate) {
    setEditingId(null)
    reset(buildDefaultForm(date))
  }

  function handleSelectDate(date: Date) {
    setSelectedDate(date)
    setCurrentMonth(startOfMonth(date))
  }

  async function onSubmit(values: EventFormValues) {
    setErrorMessage(null)
    const payload = {
      title: values.title,
      description: values.description?.trim() || null,
      start_time: new Date(values.start_time).toISOString(),
      end_time: new Date(values.end_time).toISOString(),
      location: values.location?.trim() || null,
    }
    if (editingId) {
      await safeExecute(() => schedulerApi.updateEvent(editingId, payload), setErrorMessage)
    } else {
      await safeExecute(() => schedulerApi.createEvent(payload), setErrorMessage)
    }
    await loadEvents(true)
    resetForm(new Date(payload.start_time))
  }

  async function handleDeleteEvent(item: Event) {
    if (!window.confirm(`Delete event "${item.title}"?`)) return
    await safeExecute(() => schedulerApi.deleteEvent(item.id), setErrorMessage)
    await loadEvents(true)
    resetForm()
  }

  function handleEditEvent(item: Event) {
    setSelectedDate(parseISO(item.start_time))
    setCurrentMonth(startOfMonth(parseISO(item.start_time)))
    setEditingId(item.id)
    reset({
      title: item.title,
      description: item.description ?? '',
      start_time: toDateTimeLocalFromIso(item.start_time),
      end_time: toDateTimeLocalFromIso(item.end_time),
      location: item.location ?? '',
    })
  }

  function handleMonthChange(nextMonth: Date) {
    const normalized = startOfMonth(nextMonth)
    setCurrentMonth(normalized)
    setSelectedDate(normalized)
  }

  return (
    <div className="flex flex-col gap-6 h-full">
      {errorMessage && (
        <div className="rounded-xl border border-rose-200 bg-rose-100 px-4 py-3 text-sm text-rose-700 shadow-sm">
          {errorMessage}
        </div>
      )}

      <div className="grid gap-7 xl:grid-cols-[minmax(320px,380px)_1fr] flex-1">
        <section className="flex flex-col gap-6">
          <Calendar
            currentMonth={currentMonth}
            events={events.map((e) => ({ id: e.id, start_time: e.start_time }))}
            selectedDate={selectedDate}
            onSelectDate={handleSelectDate}
            onMonthChange={handleMonthChange}
          />
        </section>

        <section className="flex flex-col gap-6">
          <div className="space-y-5 rounded-2xl bg-white p-6 shadow-card">
            <h2 className="text-xl font-semibold text-slate-900">
              {editingId ? 'Edit Event' : 'Create Event'}
            </h2>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Title
                <input type="text" {...register('title')} className={inputClass} />
                {errors.title && (
                  <p className="text-xs font-normal text-rose-600">{errors.title.message}</p>
                )}
              </label>

              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Description
                <textarea {...register('description')} className={textAreaClass} />
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                  Start
                  <input type="datetime-local" {...register('start_time')} className={inputClass} />
                  {errors.start_time && (
                    <p className="text-xs font-normal text-rose-600">{errors.start_time.message}</p>
                  )}
                </label>
                <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                  End
                  <input type="datetime-local" {...register('end_time')} className={inputClass} />
                  {errors.end_time && (
                    <p className="text-xs font-normal text-rose-600">{errors.end_time.message}</p>
                  )}
                </label>
              </div>

              <label className="flex flex-col gap-1 text-sm font-semibold text-slate-700">
                Location
                <input type="text" {...register('location')} className={inputClass} />
              </label>

              <div className="flex flex-wrap gap-3">
                <button type="submit" className={primaryBtnClass} disabled={isSubmitting}>
                  {editingId ? 'Update Event' : 'Add Event'}
                </button>
                {editingId && (
                  <button type="button" className={secondaryBtnClass} onClick={() => resetForm()}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </div>

          <div className="space-y-4 rounded-2xl bg-white p-6 shadow-card">
            <h2 className="text-xl font-semibold text-slate-900">
              Events on {format(selectedDate, 'PPPP')}
            </h2>
            {loading ? (
              <p className="text-sm text-slate-500">Loading events…</p>
            ) : eventsForSelectedDate.length === 0 ? (
              <p className="text-sm text-slate-500">No events scheduled.</p>
            ) : (
              <ul className="flex flex-col gap-4">
                {eventsForSelectedDate.map((item) => (
                  <li
                    key={item.id}
                    className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="space-y-2 text-sm text-slate-600">
                      <strong className="block text-base font-semibold text-slate-900">
                        {item.title}
                      </strong>
                      <div>
                        {format(parseISO(item.start_time), 'p')} —{' '}
                        {format(parseISO(item.end_time), 'p')}
                      </div>
                      {item.location && (
                        <div className="flex items-center gap-1">
                          📍 <span>{item.location}</span>
                        </div>
                      )}
                      {item.description && (
                        <p className="text-sm leading-relaxed text-slate-600">{item.description}</p>
                      )}
                      {item.reminders.length > 0 && (
                        <div className="text-xs uppercase tracking-wide text-slate-500">
                          Reminders:{' '}
                          {item.reminders
                            .map((rem) => format(parseISO(rem.remind_at), 'Pp'))
                            .join(', ')}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-2">
                      <button
                        type="button"
                        className={secondaryBtnClass}
                        onClick={() => handleEditEvent(item)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className={dangerBtnClass}
                        onClick={() => handleDeleteEvent(item)}
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
