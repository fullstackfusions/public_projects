import { apiClient } from '../../lib/api-client'
import type { CreateTodoDTO, Todo, UpdateTodoDTO } from './types'

const BASE = (import.meta.env.VITE_TODO_API_BASE ?? '/todo-api').replace(/\/$/, '')

const url = (path: string) => `${BASE}${path}`

export const todoApi = {
  async list(): Promise<Todo[]> {
    const { data } = await apiClient.get<Todo[]>(url('/todos'))
    return data
  },
  async create(payload: CreateTodoDTO): Promise<Todo> {
    const { data } = await apiClient.post<Todo>(url('/todos'), payload)
    return data
  },
  async update(id: string, payload: UpdateTodoDTO): Promise<Todo> {
    const { data } = await apiClient.put<Todo>(url(`/todos/${id}`), payload)
    return data
  },
  async patch(id: string, payload: Pick<UpdateTodoDTO, 'completed'>): Promise<Todo> {
    const { data } = await apiClient.patch<Todo>(url(`/todos/${id}`), payload)
    return data
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(url(`/todos/${id}`))
  },
}
