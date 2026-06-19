import { z } from 'zod'

export const CorporationSchema = z.object({
  id: z.string(),
  name: z.string(),
  corp_number: z.string().nullish(),
  business_number: z.string().nullish(),
  gst_hst_number: z.string().nullish(),
  province: z.string().nullish(),
  fiscal_year_end_month: z.number().int().min(1).max(12),
  incorporation_date: z.string(),
  contact_email: z.string().email().nullish(),
  contact_phone: z.string().nullish(),
  created_at: z.string(),
})

export const CorporationFormSchema = z.object({
  name: z.string().min(1, 'Corporation name is required'),
  corp_number: z.string().optional(),
  business_number: z.string().optional(),
  gst_hst_number: z.string().optional(),
  province: z.string().optional(),
  fiscal_year_end_month: z.number().int().min(1).max(12),
  incorporation_date: z.string().min(1, 'Incorporation date is required'),
  contact_email: z.string().email('Invalid email').optional().or(z.literal('')),
  contact_phone: z.string().optional(),
})

export const TaxFilingSchema = z.object({
  id: z.string(),
  corp_id: z.string(),
  filing_type: z.string(),
  period_label: z.string(),
  due_date: z.string(),
  status: z.string(),
  scheduler_event_id: z.number().nullish(),
})

export type CorporationFormValues = z.infer<typeof CorporationFormSchema>
