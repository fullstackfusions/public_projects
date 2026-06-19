import axios from 'axios'
import type { InvestmentParams, MortgageParams, SalaryProjectionParams } from '../../api/finance'

const BASE = (import.meta.env.VITE_FINANCE_API_BASE ?? '/finance-api').replace(/\/$/, '')
const client = axios.create({ baseURL: BASE })

type Kind = 'investment' | 'mortgage' | 'salary_projection'

export async function financeCompute<
  TParams extends InvestmentParams | MortgageParams | SalaryProjectionParams,
>(kind: Kind, params: TParams): Promise<unknown> {
  const { data } = await client.post<{ ok: boolean; result: unknown }>('/compute', { kind, params })
  return data.result
}
