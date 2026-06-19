import {
  Download as DownloadIcon,
  Home as HomeIcon,
  CalendarMonth as CalendarIcon,
  Percent as PercentIcon,
  AttachMoney as MoneyIcon,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  InputAdornment,
  Paper,
  Slider,
  TextField,
  Typography,
} from "@mui/material";
import { FormEvent, useMemo, useState } from "react";
import { financeCompute, type MortgageParams } from "../../../api/finance";
import { downloadCsv } from "../../../utils/downloadCsv";

type ScheduleRow = {
  month: number;
  year: number;
  scheduledPayment: number;
  extraMonthlyPaid: number;
  extraAnnualPaid: number;
  totalPayment: number;
  interest: number;
  principalPaid: number;
  balance: number;
  cumulativeInterest: number;
  cumulativePrincipal: number;
};

type MortgageSummary = {
  scenario: string;
  months: number;
  years: number;
  totalInterest: number;
  totalPaid: number;
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const formatCurrencyPrecise = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);

export function MortgagePage() {
  const [params, setParams] = useState<MortgageParams>({
    principal: 350000,
    annual_rate: 6.5,
    years: 30,
    monthly_payment: undefined,
    extra_monthly: 0,
    extra_annual: 0,
    annual_lump_month: 12,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [schedule, setSchedule] = useState<ScheduleRow[] | null>(null);
  const [summary, setSummary] = useState<MortgageSummary | null>(null);

  // Compute default monthly payment for display
  const estimatedPayment = useMemo(() => {
    const n = params.years * 12;
    const r = params.annual_rate / 100 / 12;
    if (r === 0) return params.principal / n;
    const factor = Math.pow(1 + r, n);
    return (params.principal * (r * factor)) / (factor - 1);
  }, [params.principal, params.annual_rate, params.years]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await financeCompute("mortgage", params);
      setSchedule(result.schedule);
      setSummary(result.summary);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to compute";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setParams({
      principal: 350000,
      annual_rate: 6.5,
      years: 30,
      monthly_payment: undefined,
      extra_monthly: 0,
      extra_annual: 0,
      annual_lump_month: 12,
    });
    setSchedule(null);
    setSummary(null);
    setError(null);
  }

  // Get yearly data for chart
  const yearlyData = useMemo(() => {
    if (!schedule || schedule.length === 0) return [];
    return schedule.filter((row) => row.month % 12 === 0 || row.month === schedule.length);
  }, [schedule]);

  return (
    <Box sx={{ height: "100%", overflow: "auto" }}>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Mortgage Calculator
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Calculate your mortgage payments and see the amortization schedule
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Input Form */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              borderRadius: 3,
              border: 1,
              borderColor: "divider",
              bgcolor: "background.paper",
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
              <HomeIcon color="primary" />
              <Typography variant="h6" fontWeight="bold">
                Mortgage Details
              </Typography>
            </Box>

            <form onSubmit={handleSubmit}>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <TextField
                  label="Loan Amount"
                  type="number"
                  value={params.principal}
                  onChange={(e) =>
                    setParams((p) => ({
                      ...p,
                      principal: Number(e.target.value),
                    }))
                  }
                  fullWidth
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">$</InputAdornment>
                    ),
                  }}
                />

                <Box>
                  <Typography variant="body2" fontWeight="medium" gutterBottom>
                    Interest Rate: {params.annual_rate}%
                  </Typography>
                  <Slider
                    value={params.annual_rate}
                    onChange={(_, value) =>
                      setParams((p) => ({
                        ...p,
                        annual_rate: value as number,
                      }))
                    }
                    min={1}
                    max={15}
                    step={0.125}
                    marks={[
                      { value: 3, label: "3%" },
                      { value: 6, label: "6%" },
                      { value: 9, label: "9%" },
                      { value: 12, label: "12%" },
                    ]}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(v) => `${v}%`}
                  />
                </Box>

                <Box>
                  <Typography variant="body2" fontWeight="medium" gutterBottom>
                    Loan Term: {params.years} years
                  </Typography>
                  <Slider
                    value={params.years}
                    onChange={(_, value) =>
                      setParams((p) => ({ ...p, years: value as number }))
                    }
                    min={5}
                    max={30}
                    step={5}
                    marks={[
                      { value: 10, label: "10y" },
                      { value: 15, label: "15y" },
                      { value: 20, label: "20y" },
                      { value: 30, label: "30y" },
                    ]}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(v) => `${v}y`}
                  />
                </Box>

                {/* Estimated Payment Display */}
                <Box
                  sx={{
                    bgcolor: "primary.50",
                    borderRadius: 2,
                    p: 2,
                    textAlign: "center",
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    Estimated Monthly Payment
                  </Typography>
                  <Typography
                    variant="h5"
                    fontWeight="bold"
                    color="primary.main"
                  >
                    {formatCurrencyPrecise(estimatedPayment)}
                  </Typography>
                </Box>

                <Divider>
                  <Chip label="Extra Payments" size="small" />
                </Divider>

                <TextField
                  label="Extra Monthly Payment"
                  type="number"
                  value={params.extra_monthly}
                  onChange={(e) =>
                    setParams((p) => ({
                      ...p,
                      extra_monthly: Number(e.target.value),
                    }))
                  }
                  fullWidth
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">$</InputAdornment>
                    ),
                  }}
                  helperText="Additional amount paid each month"
                />

                <TextField
                  label="Extra Annual Payment"
                  type="number"
                  value={params.extra_annual}
                  onChange={(e) =>
                    setParams((p) => ({
                      ...p,
                      extra_annual: Number(e.target.value),
                    }))
                  }
                  fullWidth
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">$</InputAdornment>
                    ),
                  }}
                  helperText="Lump sum payment once per year"
                />

                <Box sx={{ display: "flex", gap: 2 }}>
                  <Button
                    type="submit"
                    variant="contained"
                    size="large"
                    disabled={loading}
                    fullWidth
                    sx={{ py: 1.5 }}
                  >
                    {loading ? "Calculating..." : "Calculate"}
                  </Button>
                  <Button
                    type="button"
                    variant="outlined"
                    size="large"
                    onClick={handleReset}
                    sx={{ py: 1.5, minWidth: 100 }}
                  >
                    Reset
                  </Button>
                </Box>
              </Box>
            </form>
          </Paper>
        </Grid>

        {/* Results */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {/* Summary Cards */}
            {summary && (
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Card
                    elevation={0}
                    sx={{
                      bgcolor: "primary.main",
                      color: "primary.contrastText",
                      borderRadius: 3,
                    }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1,
                          mb: 1,
                        }}
                      >
                        <MoneyIcon fontSize="small" />
                        <Typography variant="body2" sx={{ opacity: 0.9 }}>
                          Monthly Payment
                        </Typography>
                      </Box>
                      <Typography variant="h4" fontWeight="bold">
                        {formatCurrencyPrecise(estimatedPayment)}
                      </Typography>
                      <Typography variant="body2" sx={{ opacity: 0.8, mt: 1 }}>
                        Principal & Interest
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid size={{ xs: 12, sm: 4 }}>
                  <Card
                    elevation={0}
                    sx={{
                      bgcolor: "error.50",
                      borderRadius: 3,
                      border: 1,
                      borderColor: "error.200",
                    }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1,
                          mb: 1,
                        }}
                      >
                        <PercentIcon fontSize="small" color="error" />
                        <Typography variant="body2" color="error.dark">
                          Total Interest
                        </Typography>
                      </Box>
                      <Typography
                        variant="h4"
                        fontWeight="bold"
                        color="error.dark"
                      >
                        {formatCurrency(summary.totalInterest)}
                      </Typography>
                      <Typography
                        variant="body2"
                        color="error.dark"
                        sx={{ opacity: 0.8, mt: 1 }}
                      >
                        Over loan lifetime
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid size={{ xs: 12, sm: 4 }}>
                  <Card
                    elevation={0}
                    sx={{
                      bgcolor: "success.50",
                      borderRadius: 3,
                      border: 1,
                      borderColor: "success.200",
                    }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1,
                          mb: 1,
                        }}
                      >
                        <CalendarIcon fontSize="small" color="success" />
                        <Typography variant="body2" color="success.dark">
                          Payoff Time
                        </Typography>
                      </Box>
                      <Typography
                        variant="h4"
                        fontWeight="bold"
                        color="success.dark"
                      >
                        {summary.years.toFixed(1)} years
                      </Typography>
                      <Chip
                        label={`${summary.months} months`}
                        size="small"
                        color="success"
                        sx={{ mt: 1 }}
                      />
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}

            {/* Additional Summary */}
            {summary && (
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  borderRadius: 3,
                  border: 1,
                  borderColor: "divider",
                }}
              >
                <Typography variant="h6" fontWeight="bold" gutterBottom>
                  Loan Summary
                </Typography>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 6, md: 3 }}>
                    <Typography variant="body2" color="text.secondary">
                      Principal
                    </Typography>
                    <Typography variant="h6" fontWeight="bold">
                      {formatCurrency(params.principal)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 6, md: 3 }}>
                    <Typography variant="body2" color="text.secondary">
                      Total Interest
                    </Typography>
                    <Typography variant="h6" fontWeight="bold" color="error.main">
                      {formatCurrency(summary.totalInterest)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 6, md: 3 }}>
                    <Typography variant="body2" color="text.secondary">
                      Total Paid
                    </Typography>
                    <Typography variant="h6" fontWeight="bold">
                      {formatCurrency(summary.totalPaid)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 6, md: 3 }}>
                    <Typography variant="body2" color="text.secondary">
                      Interest/Principal
                    </Typography>
                    <Typography variant="h6" fontWeight="bold">
                      {((summary.totalInterest / params.principal) * 100).toFixed(1)}%
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>
            )}

            {/* Chart */}
            {yearlyData.length > 0 && (
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  borderRadius: 3,
                  border: 1,
                  borderColor: "divider",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    mb: 3,
                  }}
                >
                  <Typography variant="h6" fontWeight="bold">
                    Amortization Chart
                  </Typography>
                  <Button
                    startIcon={<DownloadIcon />}
                    size="small"
                    variant="outlined"
                    onClick={() => downloadCsv("mortgage_schedule.csv", schedule!)}
                  >
                    Export CSV
                  </Button>
                </Box>
                <Box sx={{ height: 350 }}>
                  <MortgageChart data={yearlyData} principal={params.principal} />
                </Box>
              </Paper>
            )}

            {/* Empty State */}
            {!schedule && (
              <Paper
                elevation={0}
                sx={{
                  p: 6,
                  borderRadius: 3,
                  border: 1,
                  borderColor: "divider",
                  textAlign: "center",
                }}
              >
                <HomeIcon sx={{ fontSize: 64, color: "grey.300", mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  Calculate Your Mortgage
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Enter your mortgage details and click "Calculate" to see the
                  amortization schedule
                </Typography>
              </Paper>
            )}
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

// Mortgage Chart Component
function MortgageChart({
  data,
  principal,
}: {
  data: ScheduleRow[];
  principal: number;
}) {
  const padding = { top: 20, right: 20, bottom: 40, left: 70 };
  const width = 800;
  const height = 350;

  const maxBalance = principal;
  const maxYear = Math.max(...data.map((d) => d.year));
  const maxInterest = Math.max(...data.map((d) => d.cumulativeInterest));

  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const xScale = (year: number) =>
    padding.left + (year / maxYear) * innerW;
  const yScale = (value: number) =>
    padding.top + innerH - (value / Math.max(maxBalance, maxInterest)) * innerH;

  // Create paths
  const balancePath = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.year)} ${yScale(d.balance)}`)
    .join(" ");
  const balanceArea =
    `M ${xScale(data[0]?.year || 1)} ${yScale(0)} ` +
    data.map((d) => `L ${xScale(d.year)} ${yScale(d.balance)}`).join(" ") +
    ` L ${xScale(maxYear)} ${yScale(0)} Z`;

  const interestPath = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.year)} ${yScale(d.cumulativeInterest)}`)
    .join(" ");
  const interestArea =
    `M ${xScale(data[0]?.year || 1)} ${yScale(0)} ` +
    data.map((d) => `L ${xScale(d.year)} ${yScale(d.cumulativeInterest)}`).join(" ") +
    ` L ${xScale(maxYear)} ${yScale(0)} Z`;

  // Y-axis ticks
  const maxVal = Math.max(maxBalance, maxInterest);
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((p) => p * maxVal);

  // X-axis ticks
  const xTicks = data.filter((_, i) => i % Math.ceil(data.length / 6) === 0 || i === data.length - 1);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "100%" }}>
      {/* Grid lines */}
      {yTicks.map((t, i) => (
        <line
          key={i}
          x1={padding.left}
          y1={yScale(t)}
          x2={width - padding.right}
          y2={yScale(t)}
          stroke="#f1f5f9"
          strokeDasharray="4"
        />
      ))}

      {/* Areas */}
      <path d={balanceArea} fill="#6366f1" fillOpacity={0.3} />
      <path d={interestArea} fill="#ef4444" fillOpacity={0.3} />

      {/* Lines */}
      <path d={balancePath} fill="none" stroke="#6366f1" strokeWidth={3} />
      <path d={interestPath} fill="none" stroke="#ef4444" strokeWidth={3} />

      {/* Data points */}
      {data.filter((_, i) => i % Math.ceil(data.length / 10) === 0 || i === data.length - 1).map((d) => (
        <g key={d.year}>
          <circle cx={xScale(d.year)} cy={yScale(d.balance)} r={4} fill="#6366f1" />
          <circle cx={xScale(d.year)} cy={yScale(d.cumulativeInterest)} r={4} fill="#ef4444" />
        </g>
      ))}

      {/* Y-axis labels */}
      {yTicks.map((t, i) => (
        <text
          key={i}
          x={padding.left - 10}
          y={yScale(t)}
          textAnchor="end"
          alignmentBaseline="middle"
          fontSize={12}
          fill="#64748b"
        >
          ${(t / 1000).toFixed(0)}k
        </text>
      ))}

      {/* X-axis labels */}
      {xTicks.map((d) => (
        <text
          key={d.year}
          x={xScale(d.year)}
          y={height - padding.bottom + 20}
          textAnchor="middle"
          fontSize={12}
          fill="#64748b"
        >
          Year {d.year}
        </text>
      ))}

      {/* Legend */}
      <g transform={`translate(${padding.left + 20}, ${padding.top})`}>
        <rect width={12} height={12} fill="#6366f1" rx={2} />
        <text x={18} y={10} fontSize={12} fill="#334155">
          Remaining Balance
        </text>
        <rect x={160} width={12} height={12} fill="#ef4444" rx={2} />
        <text x={178} y={10} fontSize={12} fill="#334155">
          Total Interest Paid
        </text>
      </g>

      {/* Axes */}
      <line
        x1={padding.left}
        y1={padding.top}
        x2={padding.left}
        y2={height - padding.bottom}
        stroke="#94a3b8"
      />
      <line
        x1={padding.left}
        y1={height - padding.bottom}
        x2={width - padding.right}
        y2={height - padding.bottom}
        stroke="#94a3b8"
      />
    </svg>
  );
}
