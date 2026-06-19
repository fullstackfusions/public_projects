import axios from "axios";

const FINANCE_API_BASE = (
  import.meta.env.VITE_FINANCE_API_BASE ?? "/finance-api"
).replace(/\/$/, "");
const client = axios.create({ baseURL: FINANCE_API_BASE });

type Kind = "investment" | "mortgage" | "salary_projection";

export type InvestmentParams = {
  current_balance: number;
  monthly_payment: number;
  cagr_percent: number;
  years: number;
  contribution_timing: "start" | "end";
  lumpsums?: { month: number; amount: number }[];
};

export type MortgageParams = {
  principal: number;
  annual_rate: number;
  years: number;
  monthly_payment?: number;
  extra_monthly?: number;
  extra_annual?: number;
  annual_lump_month?: number;
};

export type SalaryProjectionParams = {
  monthly_salary: number;
  yearly_increment_percent: number;
  monthly_expense: number;
  yearly_inflation_percent: number;
  years: number;
  annual_return_percent: number;
};

export async function financeCompute<
  TParams extends InvestmentParams | MortgageParams | SalaryProjectionParams,
>(kind: Kind, params: TParams) {
  const { data } = await client.post<{ ok: boolean; result: any }>("/compute", {
    kind,
    params,
  });
  return data.result;
}
