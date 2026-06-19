import { http, HttpResponse } from 'msw'

const SCHEDULER = '/scheduler-api'

export const schedulerHandlers = [
  http.get(`${SCHEDULER}/events`, () => {
    return HttpResponse.json([
      {
        id: 1,
        title: 'Team standup',
        description: 'Daily sync',
        start_time: '2026-05-19T09:00:00.000Z',
        end_time: '2026-05-19T09:30:00.000Z',
        location: 'Zoom',
        reminders: [],
      },
      {
        id: 2,
        title: 'Lunch with client',
        description: null,
        start_time: '2026-05-19T12:00:00.000Z',
        end_time: '2026-05-19T13:00:00.000Z',
        location: null,
        reminders: [],
      },
    ])
  }),

  http.post(`${SCHEDULER}/events`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(
      { id: 99, reminders: [], ...body },
      { status: 201 },
    )
  }),

  http.put(`${SCHEDULER}/events/:id`, async ({ request, params }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ id: Number(params.id), reminders: [], ...body })
  }),

  http.delete(`${SCHEDULER}/events/:id`, () => {
    return new HttpResponse(null, { status: 204 })
  }),
]

export const handlers = [...schedulerHandlers]
