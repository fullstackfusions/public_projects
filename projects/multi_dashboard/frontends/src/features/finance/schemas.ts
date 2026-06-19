import { z } from 'zod'

export const InvestmentParamsSchema = z.object({
  current_balance: z.number().nonnegative(),
  monthly_payment: z.number().nonnegative(),
  cagr_percent: z.number(),
  years: z.number().int().positive(),
  contribution_timing: z.enum(['start', 'end']),
  lumpsums: z
    .array(z.object({ month: z.number().int(), amount: z.number() }))
    .optional(),
})

export const MortgageParamsSchema = z.object({
  principal: z.number().positive(),
  annual_rate: z.number().positive(),
  years: z.number().int().positive(),
  monthly_payment: z.number().optional(),
  extra_monthly: z.number().optional(),
  extra_annual: z.number().optional(),
  annual_lump_month: z.number().int().optional(),
})

export const SalaryParamsSchema = z.object({
  monthly_salary: z.number().positive(),
  yearly_increment_percent: z.number(),
  monthly_expense: z.number().nonnegative(),
  yearly_inflation_percent: z.number(),
  years: z.number().int().positive(),
  annual_return_percent: z.number(),
})
