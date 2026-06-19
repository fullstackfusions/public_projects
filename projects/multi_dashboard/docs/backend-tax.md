# Tax Backend — Corporate Tax Tracking

**Port:** 8007 | **Stack:** FastAPI + MongoDB (Motor async driver)

Manages corporation profiles, tax filing schedules, and Nil T2 reports. The only service in the project that uses MongoDB — a NoSQL document database instead of relational SQL.

**API docs:** http://localhost:8007/docs  
**Vite proxy:** `/tax-api` → `http://localhost:8007`

---

## What You'll Learn

- MongoDB basics — documents, collections, and querying
- When to choose NoSQL over SQL
- Using Motor (async MongoDB driver for Python)
- Embedding data in documents vs. using references (SQL joins equivalent)
- Domain-specific logic — Canadian fiscal date calculations

---

## SQL vs MongoDB — When to Use Which

This service uses MongoDB because tax data has a flexible, document-like structure. Each corporation has different filing frequencies, fiscal year ends, and report layouts.

| | PostgreSQL (SQL) | MongoDB |
|-|-----------------|---------|
| Data shape | Fixed schema (columns) | Flexible schema (nested documents) |
| Relationships | JOINs between tables | Embed or reference |
| Best for | Structured, relational data | Variable structure, nested data |
| Used in this project | auth, scheduler, todo | tax |

---

## How It Works

```
POST /corporations           → create a corporation record
GET  /corporations/{id}      → get corp + its upcoming filings
POST /corporations/{id}/filings → add a filing record
GET  /corporations/{id}/nil-t2  → generate a Nil T2 report
```

When a corporation is created, the service automatically schedules the three recurring Canadian corporate filings:
- **Annual Return** — due within 6 months of fiscal year end
- **GST/HST** — quarterly or annually depending on registration
- **T2 Corporate Tax** — due 6 months after fiscal year end

---

## Project Structure

```
backends/tax-py/
└── app/
    ├── main.py             # App factory
    ├── models/             # Pydantic document models
    ├── crud/               # MongoDB queries
    ├── domain/
    │   ├── tax_dates.py    # Fiscal date calculations
    │   └── nil_t2.py       # Nil T2 report builder
    └── routers/
        ├── corporations.py
        ├── filings.py
        └── nil_t2.py
```

---

## MongoDB Data Structure

MongoDB stores data as JSON-like documents in collections:

**`corporations` collection:**
```json
{
  "_id": "uuid",
  "name": "Acme Corp",
  "business_number": "123456789",
  "fiscal_year_end_month": 12,
  "gst_hst_filing_frequency": "quarterly"
}
```

**`tax_filings` collection:**
```json
{
  "_id": "uuid",
  "corp_id": "uuid",
  "kind": "t2",
  "due_date": "2026-06-30",
  "status": "upcoming"
}
```

Notice that filings reference `corp_id` rather than embedding inside the corporation document. This makes it easy to query filings separately.

---

## Try It

```bash
TOKEN=$(curl -s -X POST http://localhost:8005/auth/token \
  -d "username=demo&password=demo123" | jq -r .access_token)

# Create a corporation
curl -X POST http://localhost:8007/corporations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Startup Inc",
    "business_number": "123456789",
    "fiscal_year_end_month": 12,
    "gst_hst_filing_frequency": "quarterly"
  }'
```
