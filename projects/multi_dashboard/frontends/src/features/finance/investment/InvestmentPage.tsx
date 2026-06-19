import {
  Download as DownloadIcon,
  TrendingUp as TrendingUpIcon,
  AccountBalance as AccountBalanceIcon,
  Savings as SavingsIcon,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControl,
  Grid,
  InputAdornment,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Slider,
  TextField,
  Typography,
} from "@mui/material";
import { FormEvent, useMemo, useState } from "react";
import { financeCompute, type InvestmentParams } from "../../../api/finance";
import { downloadCsv } from "../../../utils/downloadCsv";

type MonthlyRow = {
  month: number;
  principal: number;
  growth: number;
  total: number;
};
type YearlyRow = {
  year: number;
  principal: number;
  growth: number;
  total: number;
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const formatPercent = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value / 100);

export function InvestmentPage() {
  const [params, setParams] = useState<InvestmentParams>({
    current_balance: 10000,
    monthly_payment: 500,
    cagr_percent: 10,
    years: 20,
    contribution_timing: "end",
    lumpsums: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [monthly, setMonthly] = useState<MonthlyRow[] | null>(null);
  const [yearly, setYearly] = useState<YearlyRow[] | null>(null);

  const final = useMemo(
    () => (monthly && monthly.length ? monthly[monthly.length - 1] : null),
    [monthly]
  );

  const growthPercent = useMemo(() => {
    if (!final || final.principal === 0) return 0;
    return ((final.growth / final.principal) * 100);
  }, [final]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await financeCompute("investment", params);
      setMonthly(result.monthly);
      setYearly(result.yearly);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to compute";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setParams({
      current_balance: 10000,
      monthly_payment: 500,
      cagr_percent: 10,
      years: 20,
      contribution_timing: "end",
      lumpsums: [],
    });
    setMonthly(null);
    setYearly(null);
    setError(null);
  }

  return (
    <Box sx={{ height: "100%", overflow: "auto" }}>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Investment Calculator
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Project your investment growth with compound interest over time
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
              <SavingsIcon color="primary" />
              <Typography variant="h6" fontWeight="bold">
                Investment Parameters
              </Typography>
            </Box>

            <form onSubmit={handleSubmit}>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <TextField
                  label="Initial Investment"
                  type="number"
                  value={params.current_balance}
                  onChange={(e) =>
                    setParams((p) => ({
                      ...p,
                      current_balance: Number(e.target.value),
                    }))
                  }
                  fullWidth
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">$</InputAdornment>
                    ),
                  }}
                />

                <TextField
                  label="Monthly Contribution"
                  type="number"
                  value={params.monthly_payment}
                  onChange={(e) =>
                    setParams((p) => ({
                      ...p,
                      monthly_payment: Number(e.target.value),
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
                    Expected Annual Return: {params.cagr_percent}%
                  </Typography>
                  <Slider
                    value={params.cagr_percent}
                    onChange={(_, value) =>
                      setParams((p) => ({
                        ...p,
                        cagr_percent: value as number,
                      }))
                    }
                    min={1}
                    max={25}
                    step={0.5}
                    marks={[
                      { value: 5, label: "5%" },
                      { value: 10, label: "10%" },
                      { value: 15, label: "15%" },
                      { value: 20, label: "20%" },
                    ]}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(v) => `${v}%`}
                  />
                </Box>

                <Box>
                  <Typography variant="body2" fontWeight="medium" gutterBottom>
                    Investment Period: {params.years} years
                  </Typography>
                  <Slider
                    value={params.years}
                    onChange={(_, value) =>
                      setParams((p) => ({ ...p, years: value as number }))
                    }
                    min={1}
                    max={40}
                    step={1}
                    marks={[
                      { value: 10, label: "10y" },
                      { value: 20, label: "20y" },
                      { value: 30, label: "30y" },
                    ]}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(v) => `${v}y`}
                  />
                </Box>

                <FormControl fullWidth>
                  <InputLabel>Contribution Timing</InputLabel>
                  <Select
                    value={params.contribution_timing}
                    label="Contribution Timing"
                    onChange={(e) =>
                      setParams((p) => ({
                        ...p,
                        contribution_timing: e.target.value as "start" | "end",
                      }))
                    }
                  >
                    <MenuItem value="end">End of Month</MenuItem>
                    <MenuItem value="start">Beginning of Month</MenuItem>
                  </Select>
                </FormControl>

                <Divider />

                <Box sx={{ display: "flex", gap: 2 }}>
                  <Button
                    type="submit"
                    variant="contained"
                    size="large"
                    disabled={loading}
                    fullWidth
                    sx={{ py: 1.5 }}
                  >
                    {loading ? "Calculating..." : "Calculate Growth"}
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
            {final && (
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
                        <AccountBalanceIcon fontSize="small" />
                        <Typography variant="body2" sx={{ opacity: 0.9 }}>
                          Total Value
                        </Typography>
                      </Box>
                      <Typography variant="h4" fontWeight="bold">
                        {formatCurrency(final.total)}
                      </Typography>
                      <Typography variant="body2" sx={{ opacity: 0.8, mt: 1 }}>
                        After {params.years} years
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid size={{ xs: 12, sm: 4 }}>
                  <Card
                    elevation={0}
                    sx={{
                      bgcolor: "grey.100",
                      borderRadius: 3,
                      border: 1,
                      borderColor: "divider",
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
                        <SavingsIcon fontSize="small" color="action" />
                        <Typography variant="body2" color="text.secondary">
                          Principal Invested
                        </Typography>
                      </Box>
                      <Typography variant="h4" fontWeight="bold">
                        {formatCurrency(final.principal)}
                      </Typography>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mt: 1 }}
                      >
                        Your contributions
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
                        <TrendingUpIcon fontSize="small" color="success" />
                        <Typography variant="body2" color="success.dark">
                          Investment Growth
                        </Typography>
                      </Box>
                      <Typography
                        variant="h4"
                        fontWeight="bold"
                        color="success.dark"
                      >
                        {formatCurrency(final.growth)}
                      </Typography>
                      <Chip
                        label={`+${growthPercent.toFixed(0)}% return`}
                        size="small"
                        color="success"
                        sx={{ mt: 1 }}
                      />
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}

            {/* Chart */}
            {yearly && yearly.length > 0 && (
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
                    Investment Growth Over Time
                  </Typography>
                  <Button
                    startIcon={<DownloadIcon />}
                    size="small"
                    variant="outlined"
                    onClick={() => downloadCsv("investment_schedule.csv", yearly)}
                  >
                    Export CSV
                  </Button>
                </Box>
                <Box sx={{ height: 350 }}>
                  <InvestmentChart data={yearly} />
                </Box>
              </Paper>
            )}

            {/* Yearly Breakdown Table */}
            {yearly && yearly.length > 0 && (
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
                  Yearly Breakdown
                </Typography>
                <Box sx={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr
                        style={{
                          borderBottom: "2px solid #e2e8f0",
                          textAlign: "left",
                        }}
                      >
                        <th style={{ padding: "12px 8px", fontWeight: 600 }}>
                          Year
                        </th>
                        <th
                          style={{
                            padding: "12px 8px",
                            fontWeight: 600,
                            textAlign: "right",
                          }}
                        >
                          Principal
                        </th>
                        <th
                          style={{
                            padding: "12px 8px",
                            fontWeight: 600,
                            textAlign: "right",
                          }}
                        >
                          Growth
                        </th>
                        <th
                          style={{
                            padding: "12px 8px",
                            fontWeight: 600,
                            textAlign: "right",
                          }}
                        >
                          Total
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {yearly
                        .filter((_, i) => i % 5 === 0 || i === yearly.length - 1)
                        .map((row) => (
                          <tr
                            key={row.year}
                            style={{ borderBottom: "1px solid #f1f5f9" }}
                          >
                            <td style={{ padding: "12px 8px" }}>{row.year}</td>
                            <td
                              style={{ padding: "12px 8px", textAlign: "right" }}
                            >
                              {formatCurrency(row.principal)}
                            </td>
                            <td
                              style={{
                                padding: "12px 8px",
                                textAlign: "right",
                                color: "#16a34a",
                              }}
                            >
                              {formatCurrency(row.growth)}
                            </td>
                            <td
                              style={{
                                padding: "12px 8px",
                                textAlign: "right",
                                fontWeight: 600,
                              }}
                            >
                              {formatCurrency(row.total)}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </Box>
              </Paper>
            )}

            {/* Empty State */}
            {!yearly && (
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
                <TrendingUpIcon
                  sx={{ fontSize: 64, color: "grey.300", mb: 2 }}
                />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  Calculate Your Investment Growth
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Enter your investment parameters and click "Calculate Growth"
                  to see projections
                </Typography>
              </Paper>
            )}
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

// Simple SVG Area Chart Component
function InvestmentChart({ data }: { data: YearlyRow[] }) {
  const padding = { top: 20, right: 20, bottom: 40, left: 70 };
  const width = 800;
  const height = 350;

  const maxTotal = Math.max(...data.map((d) => d.total));
  const maxYear = Math.max(...data.map((d) => d.year));

  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const xScale = (year: number) =>
    padding.left + (year / maxYear) * innerW;
  const yScale = (value: number) =>
    padding.top + innerH - (value / maxTotal) * innerH;

  // Create area paths
  const totalPath = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.year)} ${yScale(d.total)}`)
    .join(" ");
  const totalArea =
    `M ${xScale(0)} ${yScale(0)} ` +
    data.map((d) => `L ${xScale(d.year)} ${yScale(d.total)}`).join(" ") +
    ` L ${xScale(maxYear)} ${yScale(0)} Z`;

  const principalPath = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.year)} ${yScale(d.principal)}`)
    .join(" ");
  const principalArea =
    `M ${xScale(0)} ${yScale(0)} ` +
    data.map((d) => `L ${xScale(d.year)} ${yScale(d.principal)}`).join(" ") +
    ` L ${xScale(maxYear)} ${yScale(0)} Z`;

  // Y-axis ticks
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((p) => p * maxTotal);

  // X-axis ticks
  const xTicks = data.filter((_, i) => i % Math.ceil(data.length / 5) === 0 || i === data.length - 1);

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
      <path d={totalArea} fill="#818cf8" fillOpacity={0.3} />
      <path d={principalArea} fill="#22c55e" fillOpacity={0.3} />

      {/* Lines */}
      <path d={totalPath} fill="none" stroke="#6366f1" strokeWidth={3} />
      <path d={principalPath} fill="none" stroke="#22c55e" strokeWidth={3} />

      {/* Data points */}
      {data.filter((_, i) => i % Math.ceil(data.length / 10) === 0 || i === data.length - 1).map((d) => (
        <g key={d.year}>
          <circle cx={xScale(d.year)} cy={yScale(d.total)} r={4} fill="#6366f1" />
          <circle cx={xScale(d.year)} cy={yScale(d.principal)} r={4} fill="#22c55e" />
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
          Total Value
        </text>
        <rect x={120} width={12} height={12} fill="#22c55e" rx={2} />
        <text x={138} y={10} fontSize={12} fill="#334155">
          Principal
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
