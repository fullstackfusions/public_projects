import { useQueryClient } from '@tanstack/react-query'
import { useApiMutation } from '../../hooks/useApiMutation'
import { useApiQuery } from '../../hooks/useApiQuery'
import { taxApi } from './api'
import type { CorporationPayload, CorporationUpdatePayload } from './types'

const CORPS_KEY = ['tax', 'corporations'] as const
const FILINGS_KEY = ['tax', 'filings', 'upcoming'] as const

export function useCorporations() {
  const queryClient = useQueryClient()

  const corporationsQuery = useApiQuery(CORPS_KEY, () => taxApi.listCorporations())

  const createCorporation = useApiMutation(
    (payload: CorporationPayload) => taxApi.createCorporation(payload),
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: CORPS_KEY }) },
  )

  const updateCorporation = useApiMutation(
    ({ id, payload }: { id: string; payload: CorporationUpdatePayload }) =>
      taxApi.updateCorporation(id, payload),
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: CORPS_KEY }) },
  )

  const deleteCorporation = useApiMutation(
    (id: string) => taxApi.deleteCorporation(id),
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: CORPS_KEY }) },
  )

  return { corporationsQuery, createCorporation, updateCorporation, deleteCorporation }
}

export function useUpcomingFilings() {
  return useApiQuery(FILINGS_KEY, () => taxApi.listUpcomingFilings())
}
