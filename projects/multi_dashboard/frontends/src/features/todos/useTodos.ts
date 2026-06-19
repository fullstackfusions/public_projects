import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { todoApi } from './api'
import type { CreateTodoDTO, Todo, UpdateTodoDTO } from './types'

const todosKey = ['todos'] as const

export function useTodos() {
  const queryClient = useQueryClient()

  const todosQuery = useQuery({
    queryKey: todosKey,
    queryFn: async () => todoApi.list(),
  })

  const createTodo = useMutation({
    mutationFn: async (payload: CreateTodoDTO) => todoApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: todosKey })
    },
  })

  const toggleTodo = useMutation({
    mutationFn: async ({ id, completed }: { id: string; completed: boolean }) =>
      todoApi.patch(id, { completed }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: todosKey })
    },
  })

  const deleteTodo = useMutation({
    mutationFn: async (id: string) => todoApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: todosKey })
    },
  })

  const updateTodo = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: UpdateTodoDTO }) =>
      todoApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: todosKey })
    },
  })

  return { todosQuery, createTodo, toggleTodo, deleteTodo, updateTodo }
}
