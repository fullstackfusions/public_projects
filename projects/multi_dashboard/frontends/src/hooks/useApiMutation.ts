import { useMutation, type UseMutationOptions } from '@tanstack/react-query'
import { type ApiError } from '../lib/errors'

export function useApiMutation<TData, TVariables = void>(
  mutationFn: (vars: TVariables) => Promise<TData>,
  options?: Omit<UseMutationOptions<TData, ApiError, TVariables>, 'mutationFn'>,
) {
  return useMutation<TData, ApiError, TVariables>({ mutationFn, ...options })
}
