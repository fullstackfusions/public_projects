export interface Corporation {
  id: string
  name: string
  corp_number?: string | null
  business_number?: string | null
  gst_hst_number?: string | null
  province?: string | null
  fiscal_year_end_month: number
  incorporation_date: string
  contact_email?: string | null
  contact_phone?: string | null
  created_at: string
}

export type CorporationPayload = Omit<Corporation, 'id' | 'created_at'>
export type CorporationUpdatePayload = Partial<CorporationPayload>

export interface TaxFilingRecord {
  id: string
  corp_id: string
  filing_type: string
  period_label: string
  due_date: string
  status: string
  scheduler_event_id?: number | null
}

export interface CorporationWithFilings extends Corporation {
  filings: TaxFilingRecord[]
}

export interface FilingScheduleItem {
  filing_type: string
  period_label: string
  due_date: string
}

export interface UpcomingFiling extends TaxFilingRecord {
  corporation_name: string
  days_remaining: number
}

export interface NilT2Report {
  id: string
  corp_id: string
  fiscal_year_end: string
  generated_at: string
  has_income: boolean
  has_expenses: boolean
  report: {
    identification: Record<string, unknown>
    schedule_100: Record<string, number>
    schedule_125: Record<string, number>
    schedule_1: Record<string, number>
    notes: string[]
  }
}
