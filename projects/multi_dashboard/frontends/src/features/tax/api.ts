import { apiClient } from '../../lib/api-client'
import type {
  Corporation,
  CorporationPayload,
  CorporationUpdatePayload,
  CorporationWithFilings,
  FilingScheduleItem,
  NilT2Report,
  TaxFilingRecord,
  UpcomingFiling,
} from './types'

const BASE = (import.meta.env.VITE_TAX_API_BASE ?? '/tax-api').replace(/\/$/, '')

const url = (path: string) => `${BASE}${path}`

export const taxApi = {
  async listCorporations(): Promise<Corporation[]> {
    const { data } = await apiClient.get<Corporation[]>(url('/corporations'))
    return data
  },
  async getCorporation(corpId: string): Promise<CorporationWithFilings> {
    const { data } = await apiClient.get<CorporationWithFilings>(url(`/corporations/${corpId}`))
    return data
  },
  async createCorporation(payload: CorporationPayload): Promise<Corporation> {
    const { data } = await apiClient.post<Corporation>(url('/corporations'), payload)
    return data
  },
  async updateCorporation(corpId: string, payload: CorporationUpdatePayload): Promise<Corporation> {
    const { data } = await apiClient.put<Corporation>(url(`/corporations/${corpId}`), payload)
    return data
  },
  async deleteCorporation(corpId: string): Promise<void> {
    await apiClient.delete(url(`/corporations/${corpId}`))
  },
  async getFilingSchedule(corpId: string): Promise<FilingScheduleItem[]> {
    const { data } = await apiClient.get<FilingScheduleItem[]>(url(`/corporations/${corpId}/filing-schedule`))
    return data
  },
  async setupReminders(corpId: string): Promise<TaxFilingRecord[]> {
    const { data } = await apiClient.post<TaxFilingRecord[]>(url(`/corporations/${corpId}/setup-reminders`))
    return data
  },
  async updateFilingStatus(corpId: string, filingId: string, statusValue: string): Promise<TaxFilingRecord> {
    const { data } = await apiClient.put<TaxFilingRecord>(
      url(`/corporations/${corpId}/filings/${filingId}`),
      { status: statusValue },
    )
    return data
  },
  async listUpcomingFilings(): Promise<UpcomingFiling[]> {
    const { data } = await apiClient.get<UpcomingFiling[]>(url('/filings/upcoming'))
    return data
  },
  async generateNilT2(
    corpId: string,
    fiscalYearEnd: string,
    hasIncome: boolean,
    hasExpenses: boolean,
  ): Promise<NilT2Report> {
    const { data } = await apiClient.post<NilT2Report>(url(`/corporations/${corpId}/nil-t2`), {
      fiscal_year_end: fiscalYearEnd,
      has_income: hasIncome,
      has_expenses: hasExpenses,
    })
    return data
  },
  async getNilT2(corpId: string, fiscalYearEnd: string): Promise<NilT2Report> {
    const { data } = await apiClient.get<NilT2Report>(url(`/corporations/${corpId}/nil-t2/${fiscalYearEnd}`))
    return data
  },
}
