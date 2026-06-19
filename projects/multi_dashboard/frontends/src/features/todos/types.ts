export interface Todo {
  id: string
  title: string
  description: string | null
  completed: boolean
  due_date: string | null
  created_at: string
  updated_at: string
}

export interface CreateTodoDTO {
  title: string
  description?: string
}

export interface UpdateTodoDTO {
  title?: string
  description?: string
  completed?: boolean
}
