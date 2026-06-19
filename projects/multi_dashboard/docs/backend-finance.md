# Finance Backend — Financial Calculators

**Port:** 8001 | **Stack:** FastAPI (stateless — no database)

A pure computation service that calculates investment projections, mortgage payments, and salary figures. The simplest backend in the project — great starting point for learning FastAPI.

**API docs:** http://localhost:8001/docs

---

## What You'll Learn

- Building a stateless API (input → compute → output, no database needed)
- Pydantic for input validation and structured error messages
- When NOT to use a database (pure computation services don't need one)
- FastAPI request/response models
- Basic financial math (compound interest, mortgage amortization)

---

## Why No Database?

This service receives numbers, runs calculations, and returns results. There's nothing to store. This is a common real-world pattern — financial calculation APIs, unit conversion services, and recommendation engines often work this way.

Keeping it stateless means:
- No database to manage or migrate
- Easy to scale horizontally (any instance can handle any request)
- Simple to test (pure functions)

---

## Project Structure

```
backends/finance-py/
└── app/
    ├── main.py          # App factory
    └── routers/
        ├── investment.py  # Investment projection calculations
        ├── mortgage.py    # Mortgage payment calculations
        └── salary.py      # Salary and take-home pay estimates
```

---

## Endpoints

No authentication required on this service.

| Method | Path | What it calculates |
|--------|------|-------------------|
| `POST` | `/investment/compute` | Future value with compound interest |
| `POST` | `/mortgage/compute` | Monthly payment and total interest |
| `POST` | `/salary/compute` | Net pay after taxes and deductions |

---

## Try It

```bash
# Calculate investment growth
curl -X POST http://localhost:8001/investment/compute \
  -H "Content-Type: application/json" \
  -d '{
    "principal": 10000,
    "annual_rate": 0.07,
    "years": 10,
    "compound_frequency": "monthly"
  }'

# Calculate mortgage payment
curl -X POST http://localhost:8001/mortgage/compute \
  -H "Content-Type: application/json" \
  -d '{
    "principal": 300000,
    "annual_rate": 0.065,
    "amortization_years": 25
  }'
```

---

## Key Concept: Input Validation with Pydantic

FastAPI uses Pydantic models for automatic validation. If you send invalid data, you get a clear error:

```python
class InvestmentRequest(BaseModel):
    principal: float = Field(gt=0, description="Initial investment amount")
    annual_rate: float = Field(gt=0, lt=1, description="Annual rate as decimal (0.07 = 7%)")
    years: int = Field(gt=0, le=100)
```

If `annual_rate` is `5.0` instead of `0.05`, Pydantic rejects it immediately with a descriptive error — no database calls, no crashes.
