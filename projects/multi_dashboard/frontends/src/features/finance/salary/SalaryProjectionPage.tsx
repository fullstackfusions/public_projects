import {
  Savings as SavingsIcon,
  ShowChart as ShowChartIcon,
  TrendingUp as TrendingUpIcon,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  InputAdornment,
  Paper,
  Slider,
  TextField,
  Typography,
} from "@mui/material";
import { FormEvent, useState } from "react";
import {
  financeCompute,
  type SalaryProjectionParams,
} from "../../../api/finance";
import { downloadCsv } from "../../../utils/downloadCsv";
import { LineChart } from "../components/LineChart";

type YearlyRow = {
  year: number;
  annualSalary: number;
  annualExpense: number;
  annualSaving: number;
  cumulativeSavings: number;
  investmentValue: number;
};

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);

export function SalaryProjectionPage() {
  const [params, setParams] = useState<SalaryProjectionParams>({
    monthly_salary: 5000,
    yearly_increment_percent: 3,
    monthly_expense: 3000,
    yearly_inflation_percent: 3,
    years: 20,
    annual_return_percent: 18,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [yearly, setYearly] = useState<YearlyRow[] | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await financeCompute("salary_projection", params);
      setYearly(result.yearly);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err.message ?? "Compute failed");
    } finally {
      setLoading(false);
    }
  };

  const last = yearly && yearly.length ? yearly[yearly.length - 1] : null;

  return (
    <Box sx={{ maxWidth: 1200, mx: "auto", py: 4, px: 2 }}>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        Salary &amp; Savings Projection
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Project your long-term savings and investment growth based on salary,
        expenses, and expected returns.
      </Typography>

      <Grid container spacing={3}>
        {/* ── Form ── */}
        <Grid item xs={12} md={4}>
          <Paper
            elevation={0}
            sx={{ p: 3, border: "1px solid", borderColor: "divider" }}
          >
            <form onSubmit={handleSubmit}>
              <TextField
                label="Monthly Salary"
                type="number"
                fullWidth
                required
                margin="normal"
                value={params.monthly_salary}
                onChange={(e) =>
                  setParams({
                    ...params,
                    monthly_salary: Number(e.target.value),
                  })
                }
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">$</InputAdornment>
                  ),
                }}
                inputProps={{ min: 1, step: 100 }}
              />

              <TextField
                label="Monthly Expense"
                type="number"
                fullWidth
                required
                margin="normal"
                value={params.monthly_expense}
                onChange={(e) =>
                  setParams({
                    ...params,
                    monthly_expense: Number(e.target.value),
                  })
                }
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">$</InputAdornment>
                  ),
                }}
                inputProps={{ min: 0, step: 100 }}
              />

              <Box sx={{ mt: 3, mb: 1 }}>
                <Typography gutterBottom>
                  Yearly Salary Increment:{" "}
                  <strong>{params.yearly_increment_percent}%</strong>
                </Typography>
                <Slider
                  value={params.yearly_increment_percent}
                  onChange={(_, v) =>
                    setParams({
                      ...params,
                      yearly_increment_percent: v as number,
                    })
                  }
                  min={0}
                  max={30}
                  step={0.5}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(v) => `${v}%`}
                />
              </Box>

              <Box sx={{ mb: 1 }}>
                <Typography gutterBottom>
                  Yearly Expense Inflation:{" "}
                  <strong>{params.yearly_inflation_percent}%</strong>
                </Typography>
                <Slider
                  value={params.yearly_inflation_percent}
                  onChange={(_, v) =>
                    setParams({
                      ...params,
                      yearly_inflation_percent: v as number,
                    })
                  }
                  min={0}
                  max={20}
                  step={0.5}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(v) => `${v}%`}
                />
              </Box>

              <Box sx={{ mb: 1 }}>
                <Typography gutterBottom>
                  Annual Investment Return:{" "}
                  <strong>{params.annual_return_percent}%</strong>
                </Typography>
                <Slider
                  value={params.annual_return_percent}
                  onChange={(_, v) =>
                    setParams({
                      ...params,
                      annual_return_percent: v as number,
                    })
                  }
                  min={0}
                  max={40}
                  step={0.5}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(v) => `${v}%`}
                />
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography gutterBottom>
                  Projection Period: <strong>{params.years} years</strong>
                </Typography>
                <Slider
                  value={params.years}
                  onChange={(_, v) =>
                    setParams({ ...params, years: v as number })
                  }
                  min={1}
                  max={50}
                  step={1}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(v) => `${v}y`}
                />
              </Box>

              <Button
                type="submit"
                variant="contained"
                fullWidth
                disabled={loading}
                sx={{ mt: 1 }}
              >
                {loading ? "Calculating…" : "Calculate Projection"}
              </Button>
            </form>
          </Paper>
        </Grid>

        {/* ── Results ── */}
        <Grid item xs={12} md={8}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {last && yearly && (
            <>
              {/* Summary cards */}
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={4}>
                  <Card
                    elevation={0}
                    sx={{
                      border: "1px solid",
                      borderColor: "primary.light",
                      bgcolor: "primary.50",
                    }}
                  >
                    <CardContent sx={{ textAlign: "center" }}>
                      <SavingsIcon color="primary" />
                      <Typography variant="subtitle2" color="text.secondary">
                        Cumulative Savings
                      </Typography>
                      <Typography variant="h6" fontWeight={700}>
                        {fmt(last.cumulativeSavings)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Card
                    elevation={0}
                    sx={{
                      border: "1px solid",
                      borderColor: "success.light",
                      bgcolor: "success.50",
                    }}
                  >
                    <CardContent sx={{ textAlign: "center" }}>
                      <TrendingUpIcon color="success" />
                      <Typography variant="subtitle2" color="text.secondary">
                        Investment Value
                      </Typography>
                      <Typography variant="h6" fontWeight={700}>
                        {fmt(last.investmentValue)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Card
                    elevation={0}
                    sx={{
                      border: "1px solid",
                      borderColor: "info.light",
                      bgcolor: "info.50",
                    }}
                  >
                    <CardContent sx={{ textAlign: "center" }}>
                      <ShowChartIcon color="info" />
                      <Typography variant="subtitle2" color="text.secondary">
                        Investment Growth
                      </Typography>
                      <Typography variant="h6" fontWeight={700}>
                        {fmt(last.investmentValue - last.cumulativeSavings)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {/* Line chart */}
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  mb: 3,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="h6" gutterBottom>
                  Savings vs Investment Growth
                </Typography>
                <LineChart
                  data={yearly}
                  xKey="year"
                  series={[
                    {
                      key: "cumulativeSavings",
                      label: "Cumulative Savings",
                      color: "#1976d2",
                    },
                    {
                      key: "investmentValue",
                      label: "Investment Value",
                      color: "#2e7d32",
                    },
                  ]}
                  height={340}
                />
              </Paper>

              {/* Yearly breakdown table */}
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  border: "1px solid",
                  borderColor: "divider",
                  overflowX: "auto",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    mb: 1,
                  }}
                >
                  <Typography variant="h6">Yearly Breakdown</Typography>
                  <Button
                    size="small"
                    onClick={() => downloadCsv("salary-projection.csv", yearly)}
                  >
                    Export CSV
                  </Button>
                </Box>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="py-2 pr-4">Year</th>
                      <th className="py-2 pr-4 text-right">Annual Salary</th>
                      <th className="py-2 pr-4 text-right">Annual Expense</th>
                      <th className="py-2 pr-4 text-right">Annual Saving</th>
                      <th className="py-2 pr-4 text-right">
                        Cumulative Savings
                      </th>
                      <th className="py-2 text-right">Investment Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {yearly.map((r) => (
                      <tr key={r.year} className="border-b last:border-0">
                        <td className="py-1.5 pr-4">{r.year}</td>
                        <td className="py-1.5 pr-4 text-right">
                          {fmt(r.annualSalary)}
                        </td>
                        <td className="py-1.5 pr-4 text-right">
                          {fmt(r.annualExpense)}
                        </td>
                        <td className="py-1.5 pr-4 text-right">
                          {fmt(r.annualSaving)}
                        </td>
                        <td className="py-1.5 pr-4 text-right">
                          {fmt(r.cumulativeSavings)}
                        </td>
                        <td className="py-1.5 text-right">
                          {fmt(r.investmentValue)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Paper>
            </>
          )}

          {!yearly && !error && (
            <Paper
              elevation={0}
              sx={{
                p: 6,
                textAlign: "center",
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography color="text.secondary">
                Fill in your salary details and hit <strong>Calculate</strong>{" "}
                to see your savings and investment projection.
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
