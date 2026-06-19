import { useQuery, type QueryKey, type UseQueryOptions } from '@tanstack/react-query'
import { type ApiError } from '../lib/errors'

export function useApiQuery<TData>(
  queryKey: QueryKey,
  queryFn: () => Promise<TData>,
  options?: Omit<UseQueryOptions<TData, ApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<TData, ApiError>({ queryKey, queryFn, ...options })
}
