import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getMyPreferences, updateMyPreferences } from './api'
import type { UpdatePreference } from './types'

const QUERY_KEY = ['preferences', 'me']

export function useMyPreferences() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: getMyPreferences,
  })
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: UpdatePreference) => updateMyPreferences(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })
}
