import {
  CompareArrows as CompareArrowsIcon,
  Home as HomeIcon,
  TrendingUp as TrendingUpIcon,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  InputAdornment,
  Paper,
  Slider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";

type ComparisonParams = {
  homePrice: number;
  downPaymentPct: number;
  mortgageRatePct: number;
  mortgageYears: number;
  monthlyPropertyTax: number;
  monthlyMaintenance: number;
  homeAppreciationPct: number;
  yearsToCompare: number;
  monthlyRent: number;
  annualRentIncreasePct: number;
  initialInvestment: number;
  monthlyInvestment: number;
  investmentReturnPct: number;
  bearMarketDropPct: number;
  firstBearMarketYear: number;
  bearMarketFrequencyYears: number;
  inflationPct: number;
};

type YearlyPoint = {
  year: number;
  ownerNetWorth: number;
  renterNetWorth: number;
  ownerRealNetWorth: number;
  renterRealNetWorth: number;
  rentAnnual: number;
  ownerAnnualCost: number;
  totalAnnualInvestmentContribution: number;
  avgMonthlyInvestmentContribution: number;
};

const defaultParams: ComparisonParams = {
  homePrice: 450000,
  downPaymentPct: 20,
  mortgageRatePct: 6.5,
  mortgageYears: 30,
  monthlyPropertyTax: 450,
  monthlyMaintenance: 350,
  homeAppreciationPct: 3,
  yearsToCompare: 30,
  monthlyRent: 2200,
  annualRentIncreasePct: 4,
  initialInvestment: 90000,
  monthlyInvestment: 500,
  investmentReturnPct: 8,
  bearMarketDropPct: 25,
  firstBearMarketYear: 5,
  bearMarketFrequencyYears: 5,
  inflationPct: 2.5,
};

const money = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const precisePct = (value: number) => `${value.toFixed(1)}%`;

function monthlyMortgagePayment(principal: number, annualRatePct: number, years: number) {
  const n = years * 12;
  const r = annualRatePct / 100 / 12;
  if (!n) return 0;
  if (!r) return principal / n;
  const factor = Math.pow(1 + r, n);
  return (principal * (r * factor)) / (factor - 1);
}

function simulateComparison(params: ComparisonParams): YearlyPoint[] {
  const loanPrincipal = params.homePrice * (1 - params.downPaymentPct / 100);
  const downPayment = params.homePrice - loanPrincipal;
  const monthlyPayment = monthlyMortgagePayment(
    loanPrincipal,
    params.mortgageRatePct,
    params.mortgageYears,
  );

  let loanBalance = loanPrincipal;
  let homeValue = params.homePrice;
  let investmentBalance = params.initialInvestment + downPayment;
  let monthlyRent = params.monthlyRent;

  const monthlyRate = params.mortgageRatePct / 100 / 12;
  const investMonthlyRate = Math.pow(1 + params.investmentReturnPct / 100, 1 / 12) - 1;

  const points: YearlyPoint[] = [];

  for (let year = 1; year <= params.yearsToCompare; year += 1) {
    let ownerYearCost = 0;
    let rentYearCost = 0;
    let yearlyInvestmentContribution = 0;

    for (let month = 1; month <= 12; month += 1) {
      const interest = loanBalance * monthlyRate;
      const principalPayment = Math.max(0, Math.min(monthlyPayment - interest, loanBalance));
      const payment = interest + principalPayment;
      loanBalance -= principalPayment;

      const ownerMonthlyCost = payment + params.monthlyPropertyTax + params.monthlyMaintenance;
      ownerYearCost += ownerMonthlyCost;

      rentYearCost += monthlyRent;

      investmentBalance *= 1 + investMonthlyRate;
      const investFromCostGap = Math.max(ownerMonthlyCost - monthlyRent, 0);
      const monthlyContribution = params.monthlyInvestment + investFromCostGap;
      yearlyInvestmentContribution += monthlyContribution;
      investmentBalance += monthlyContribution;
    }

    if (
      year >= params.firstBearMarketYear &&
      (year - params.firstBearMarketYear) % params.bearMarketFrequencyYears === 0
    ) {
      investmentBalance *= 1 - params.bearMarketDropPct / 100;
    }

    homeValue *= 1 + params.homeAppreciationPct / 100;
    monthlyRent *= 1 + params.annualRentIncreasePct / 100;

    const inflationFactor = Math.pow(1 + params.inflationPct / 100, year);
    const ownerNetWorth = homeValue - loanBalance;
    const renterNetWorth = investmentBalance;

    points.push({
      year,
      ownerNetWorth,
      renterNetWorth,
      ownerRealNetWorth: ownerNetWorth / inflationFactor,
      renterRealNetWorth: renterNetWorth / inflationFactor,
      rentAnnual: rentYearCost,
      ownerAnnualCost: ownerYearCost,
      totalAnnualInvestmentContribution: yearlyInvestmentContribution,
      avgMonthlyInvestmentContribution: yearlyInvestmentContribution / 12,
    });
  }

  return points;
}

export function HousingComparisonPage() {
  const [params, setParams] = useState(defaultParams);

  const data = useMemo(() => simulateComparison(params), [params]);
  const final = data[data.length - 1];
  const winner = final
    ? final.ownerRealNetWorth > final.renterRealNetWorth
      ? "Buy"
      : "Rent + Invest"
    : null;

  return (
    <Box sx={{ height: "100%", overflow: "auto" }}>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Buy vs Rent + Invest
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Compare mortgage ownership against renting + investing with inflation,
          property tax, maintenance, rent growth, and bear market shock.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3, border: 1, borderColor: "divider" }}>
            <Stack spacing={2.5}>
              <Typography variant="h6" fontWeight="bold">
                Scenario Inputs
              </Typography>

              <TextField
                label="Home price"
                type="number"
                value={params.homePrice}
                onChange={(e) => setParams((p) => ({ ...p, homePrice: Number(e.target.value) }))}
                InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
              />

              <TextField
                label="Monthly rent"
                type="number"
                value={params.monthlyRent}
                onChange={(e) => setParams((p) => ({ ...p, monthlyRent: Number(e.target.value) }))}
                InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
              />

              <SliderInput label="Down payment" value={params.downPaymentPct} min={0} max={60} step={1} unit="%"
                onChange={(v) => setParams((p) => ({ ...p, downPaymentPct: v }))}
              />
              <SliderInput label="Mortgage rate" value={params.mortgageRatePct} min={1} max={12} step={0.1} unit="%"
                onChange={(v) => setParams((p) => ({ ...p, mortgageRatePct: v }))}
              />
              <TextField
                label="Property tax (monthly)"
                type="number"
                value={params.monthlyPropertyTax}
                onChange={(e) =>
                  setParams((p) => ({ ...p, monthlyPropertyTax: Number(e.target.value) }))
                }
                InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
              />
              <TextField
                label="Maintenance (monthly)"
                type="number"
                value={params.monthlyMaintenance}
                onChange={(e) =>
                  setParams((p) => ({ ...p, monthlyMaintenance: Number(e.target.value) }))
                }
                InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
              />
              <SliderInput label="Rent increase" value={params.annualRentIncreasePct} min={0} max={10} step={0.25} unit="%"
                onChange={(v) => setParams((p) => ({ ...p, annualRentIncreasePct: v }))}
              />
              <TextField
                label="Base monthly investment"
                type="number"
                value={params.monthlyInvestment}
                onChange={(e) =>
                  setParams((p) => ({ ...p, monthlyInvestment: Number(e.target.value) }))
                }
                InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
              />
              <SliderInput label="Investment return" value={params.investmentReturnPct} min={1} max={15} step={0.25} unit="%"
                onChange={(v) => setParams((p) => ({ ...p, investmentReturnPct: v }))}
              />
              <SliderInput label="Inflation" value={params.inflationPct} min={0} max={8} step={0.25} unit="%"
                onChange={(v) => setParams((p) => ({ ...p, inflationPct: v }))}
              />

              <Divider><Chip size="small" label="Stress Test" /></Divider>

              <SliderInput label="Bear market drop" value={params.bearMarketDropPct} min={0} max={60} step={1} unit="%"
                onChange={(v) => setParams((p) => ({ ...p, bearMarketDropPct: v }))}
              />
              <SliderInput label="First bear market year" value={params.firstBearMarketYear} min={1} max={params.yearsToCompare} step={1} unit="y"
                onChange={(v) => setParams((p) => ({ ...p, firstBearMarketYear: v }))}
              />
              <SliderInput label="Bear market frequency" value={params.bearMarketFrequencyYears} min={1} max={15} step={1} unit="y"
                onChange={(v) => setParams((p) => ({ ...p, bearMarketFrequencyYears: v }))}
              />
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }}>
          <Stack spacing={3}>
            {final ? (
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Card
                    elevation={0}
                    sx={{ borderRadius: 3, bgcolor: "primary.main", color: "primary.contrastText" }}
                  >
                    <CardContent>
                      <Typography variant="body2" sx={{ opacity: 0.9 }}>
                        Winner (Inflation-adjusted)
                      </Typography>
                      <Typography variant="h4" fontWeight="bold">
                        {winner}
                      </Typography>
                      <Typography variant="body2" sx={{ opacity: 0.85 }}>
                        {params.yearsToCompare}-year projection
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Card elevation={0} sx={{ borderRadius: 3, border: 1, borderColor: "divider" }}>
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Owner net worth (real)
                      </Typography>
                      <Typography variant="h5" fontWeight="bold" color="success.dark">
                        {money(final.ownerRealNetWorth)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Card elevation={0} sx={{ borderRadius: 3, border: 1, borderColor: "divider" }}>
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Renter+investor net worth (real)
                      </Typography>
                      <Typography variant="h5" fontWeight="bold" color="secondary.dark">
                        {money(final.renterRealNetWorth)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <Alert severity="info">
                    Monthly investment in year {final.year}: Base {money(params.monthlyInvestment)} + Cost gap{" "}
                    {money(Math.max(final.avgMonthlyInvestmentContribution - params.monthlyInvestment, 0))} ={" "}
                    {money(final.avgMonthlyInvestmentContribution)}
                  </Alert>
                </Grid>
              </Grid>
            ) : null}

            <Paper elevation={0} sx={{ p: 3, borderRadius: 3, border: 1, borderColor: "divider" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                <CompareArrowsIcon color="primary" />
                <Typography variant="h6" fontWeight="bold">Net Worth Comparison</Typography>
              </Box>
              <Box sx={{ height: 360 }}>
                <ComparisonChart data={data} />
              </Box>
            </Paper>

            <Paper elevation={0} sx={{ p: 3, borderRadius: 3, border: 1, borderColor: "divider" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                <TrendingUpIcon color="action" />
                <Typography variant="h6" fontWeight="bold">Annual Cost Pressure</Typography>
              </Box>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 1 }}>
                {data.slice(-6).map((d) => (
                  <Alert key={d.year} severity={d.ownerAnnualCost > d.rentAnnual ? "info" : "success"} icon={<HomeIcon fontSize="inherit" />}>
                    Year {d.year}: Owner cost {money(d.ownerAnnualCost)} vs Rent {money(d.rentAnnual)} | Avg monthly invested {money(d.avgMonthlyInvestmentContribution)}
                  </Alert>
                ))}
              </Box>
            </Paper>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}

function SliderInput({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (value: number) => void;
}) {
  return (
    <Box>
      <Typography variant="body2" fontWeight="medium" gutterBottom>
        {label}: {unit === "%" ? precisePct(value) : `${value}${unit}`}
      </Typography>
      <Slider min={min} max={max} step={step} value={value} onChange={(_, v) => onChange(v as number)} valueLabelDisplay="auto" />
    </Box>
  );
}

function ComparisonChart({ data }: { data: YearlyPoint[] }) {
  const padding = { top: 20, right: 20, bottom: 36, left: 70 };
  const width = 900;
  const height = 360;
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  if (!data.length) return null;

  const maxY = Math.max(...data.map((d) => Math.max(d.ownerRealNetWorth, d.renterRealNetWorth)));
  const maxX = data[data.length - 1]?.year ?? 1;
  const x = (year: number) => padding.left + (year / maxX) * innerW;
  const y = (value: number) => padding.top + innerH - (value / maxY) * innerH;

  const path = (key: "ownerRealNetWorth" | "renterRealNetWorth") =>
    data.map((d, i) => `${i === 0 ? "M" : "L"} ${x(d.year)} ${y(d[key])}`).join(" ");

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((r) => r * maxY);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "100%" }}>
      {yTicks.map((tick) => (
        <line key={tick} x1={padding.left} y1={y(tick)} x2={width - padding.right} y2={y(tick)} stroke="#e2e8f0" strokeDasharray="3" />
      ))}

      <path d={path("ownerRealNetWorth")} fill="none" stroke="#16a34a" strokeWidth={3} />
      <path d={path("renterRealNetWorth")} fill="none" stroke="#7c3aed" strokeWidth={3} />

      {data.filter((_, i) => i % Math.ceil(data.length / 8) === 0 || i === data.length - 1).map((d) => (
        <g key={d.year}>
          <circle cx={x(d.year)} cy={y(d.ownerRealNetWorth)} r={3.5} fill="#16a34a" />
          <circle cx={x(d.year)} cy={y(d.renterRealNetWorth)} r={3.5} fill="#7c3aed" />
          <text x={x(d.year)} y={height - 8} textAnchor="middle" fontSize={11} fill="#64748b">Y{d.year}</text>
        </g>
      ))}

      {yTicks.map((tick) => (
        <text key={`y-${tick}`} x={padding.left - 8} y={y(tick)} textAnchor="end" alignmentBaseline="middle" fontSize={11} fill="#64748b">
          {(tick / 1000).toFixed(0)}k
        </text>
      ))}

      <g transform={`translate(${padding.left + 16}, ${padding.top})`}>
        <rect width={12} height={12} fill="#16a34a" rx={2} />
        <text x={18} y={10} fontSize={12} fill="#334155">Buy (real)</text>
        <rect x={170} width={12} height={12} fill="#7c3aed" rx={2} />
        <text x={188} y={10} fontSize={12} fill="#334155">Rent + Invest (real)</text>
      </g>
    </svg>
  );
}
