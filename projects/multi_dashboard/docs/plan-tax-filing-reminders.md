# Tax Filing Reminders & Scheduler Plan

> **Status — IMPLEMENTED.** The design described below shipped as the [`tax-py`](../backends/tax-py) service and the `tax` / `corporations` / `nil-t2` frontend features. See [backend-tax.md](./backend-tax.md) for the current reference.
>
> Two intentional deltas from the original plan:
> 1. **MongoDB** was chosen instead of SQLite/SQLAlchemy (`MONGO_URI=mongodb://…/tax_db`). Document model fits the variable-shape Nil T2 report payloads better.
> 2. Cross-service reminder creation is performed via HTTP calls to the [scheduler service](./backend-scheduler.md) from `app/services/reminders.py` (not by sharing the scheduler DB).
>
> The rest of the document is kept as historical design context.

---

## Context

Corporations have three recurring tax obligations in Canada:
- **Annual Return** – filed on the anniversary of incorporation date
- **GST/HST Quarterly Return** – filed within 1 month after each fiscal quarter end
- **T2 (Corporate Income Tax)** – due 6 months after fiscal year end; full preparation requires an accountant when income/expenses exist, but a nil return (zero income, zero expenses) can be generated from corporation details alone

The goal is to:
1. Store corporation profile details and auto-generate scheduler events + reminders for all three tax deadlines using the existing scheduler service (no hands-off filing — just timely notifications)
2. For corporations with zero income/expenses, generate a pre-populated nil T2 report that maps corporation details to the required CRA schedule fields, ready to hand to an accountant or feed into a free filing tool

> **Out of scope (next phase):** Direct CRA NETFILE submission (requires CRA software certification), T2 preparation for corporations with actual income/expenses.

---

## What Exists Today

| Area | Status |
|---|---|
| `backends/scheduler-py` | FastAPI service with Event + Reminder CRUD (SQLite, SQLAlchemy). No background worker — reminders are data only. |
| `frontends/customer-portal/src/features/scheduler` | React calendar + reminder pages |
| `frontends/customer-portal/src/config/featureNavigation.ts` | Nav groups config |
| `frontends/customer-portal/src/App.tsx` | Route definitions |
| `frontends/customer-portal/vite.config.ts` | Proxy rewrites (scheduler-api, todo-api, finance-api) |
| `docker-compose.yml` | All services + volumes |

No tax-related models, routes, or UI exist anywhere in the codebase.

---

## Approach: New `tax-py` Microservice + New Frontend Feature

Follows the project's established pattern: one FastAPI service per domain, one React feature module per service.

---

## Backend: `backends/tax-py`

### File layout (mirrors `scheduler-py`)
```
backends/tax-py/
  app/
    __init__.py
    database.py      # SQLAlchemy engine + get_db (TAX_DATABASE_URL env var)
    models.py        # Corporation, TaxFilingRecord, NilT2Report
    schemas.py       # Pydantic schemas
    crud.py          # DB operations
    tax_dates.py     # Pure date-logic helpers (no DB)
    nil_t2.py        # Nil T2 report builder — maps corp details to CRA schedule fields
    main.py          # FastAPI app + all endpoints
  requirements.txt   # fastapi, uvicorn, sqlalchemy, pydantic, httpx
  Dockerfile         # FROM python:3.12-slim, pip install, uvicorn entrypoint
```

### Data Models

**`Corporation`**
```
id                    INTEGER PK
name                  VARCHAR(200) NOT NULL
corp_number           VARCHAR(50)          -- e.g. "1234567 Ontario Inc."
business_number       VARCHAR(20)          -- CRA Business Number (9 digits)
gst_hst_number        VARCHAR(15)          -- RT0001 suffix
province              VARCHAR(50)
fiscal_year_end_month INTEGER (1–12)       -- e.g. 12 = December
incorporation_date    DATE NOT NULL        -- determines Annual Return due date
contact_email         VARCHAR(200)
created_at            DATETIME
```

**`TaxFilingRecord`**
```
id            INTEGER PK
corp_id       FK → corporations.id CASCADE DELETE
filing_type   VARCHAR(30)   -- "annual_return" | "gst_hst_q1" | "gst_hst_q2" | "gst_hst_q3" | "gst_hst_q4" | "t2"
period_label  VARCHAR(50)   -- e.g. "Q1 2025 (Jan–Mar)" or "FY 2024 T2"
due_date      DATE NOT NULL
status        VARCHAR(20)   -- "pending" | "filed" | "overdue"
scheduler_event_id  INTEGER NULLABLE  -- ID of event created in scheduler-py
```

**`NilT2Report`** *(new — one per corp per fiscal year)*
```
id                  INTEGER PK
corp_id             FK → corporations.id CASCADE DELETE
fiscal_year_end     DATE NOT NULL        -- e.g. 2024-12-31
generated_at        DATETIME
has_income          BOOLEAN DEFAULT false
has_expenses        BOOLEAN DEFAULT false
report_json         TEXT                 -- serialized schedule fields (Sch 100, 125, 1)
```

### Date Logic (`tax_dates.py`)

**Annual Return due date:**
- Same month + day as `incorporation_date`, current year
- If already passed this year, return next year's date
- Reminders: 90, 60, 30, 7 days before due date

**GST/HST quarters** (based on `fiscal_year_end_month`):
- Quarter boundaries derived from fiscal year end (e.g., fiscal end = Dec → Q1 Jan–Mar, Q2 Apr–Jun, Q3 Jul–Sep, Q4 Oct–Dec)
- Each quarter due 1 month after quarter end (e.g., Q1 due April 30)
- Generate upcoming 4 quarters
- Reminders: 30, 14, 7, 1 days before due date

**T2 due date:**
- Due 6 months after fiscal year end (e.g., fiscal end Dec 31 → T2 due June 30)
- Generate for current fiscal year; if already filed, show next year
- Reminders: 90, 60, 30, 14 days before due date

### API Endpoints (`main.py`)

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/corporations` | List all corporations |
| POST | `/corporations` | Create corporation |
| GET | `/corporations/{id}` | Get corporation with filing records |
| PUT | `/corporations/{id}` | Update corporation |
| DELETE | `/corporations/{id}` | Delete corporation + cascaded records |
| GET | `/corporations/{id}/filing-schedule` | Compute upcoming deadlines for all 3 types (not persisted) |
| POST | `/corporations/{id}/setup-reminders` | Create TaxFilingRecords + call scheduler-py to create events + reminders |
| PUT | `/corporations/{corp_id}/filings/{filing_id}` | Update status (e.g., mark "filed") |
| GET | `/filings/upcoming` | All pending/overdue filings across all corps, sorted by due_date |
| POST | `/corporations/{id}/nil-t2` | Generate nil T2 report for a given fiscal year (requires has_income=false, has_expenses=false) |
| GET | `/corporations/{id}/nil-t2/{fiscal_year}` | Retrieve previously generated nil T2 report |

**Nil T2 report logic** in `nil_t2.py` (new helper module):
- Accepts corporation details + fiscal year end date
- Builds a structured dict representing key CRA T2 schedules for a nil return:
  - **Schedule 100** (Balance Sheet Information) — all zeros
  - **Schedule 125** (Income Statement Information) — all zeros
  - **Schedule 1** (Net Income for Tax Purposes reconciliation) — all zeros
  - **Identification section** — corp name, BN, address, fiscal year dates, province
- Serialized as JSON and stored in `NilT2Report.report_json`
- Frontend renders this as a human-readable, printable summary

**Scheduler integration** in `setup-reminders`:
- Uses `httpx` (sync) to call `http://scheduler-backend:8000`
- For each deadline: POST `/events` → then POST `/reminders` for each reminder offset
- Stores returned `event.id` in `TaxFilingRecord.scheduler_event_id`
- Idempotent: skips if `scheduler_event_id` already set

---

## Frontend: `frontends/customer-portal/src/features/tax/`

```
features/tax/
  types.ts                    -- Corporation, TaxFilingRecord, FilingSchedule, NilT2Report interfaces
  CorporationPage.tsx          -- Create/edit corporation profile form
  TaxDashboardPage.tsx         -- Upcoming deadlines table + "Setup Reminders" button per corp
  NilT2Page.tsx                -- Nil T2 report: income/expense toggle + generated report view
```

**`src/api/tax.ts`** — API client with base `/tax-api`:
- `listCorporations()`, `createCorporation()`, `getCorporation()`, `updateCorporation()`, `deleteCorporation()`
- `getFilingSchedule(corpId)`, `setupReminders(corpId)`
- `updateFiling(corpId, filingId, status)`
- `getUpcomingFilings()`
- `generateNilT2(corpId, fiscalYear)`, `getNilT2(corpId, fiscalYear)`

**`TaxDashboardPage`** shows:
- Table of upcoming filings across all 3 types (corp name, filing type, period, due date, days remaining, status)
- Color-coded urgency (red < 14 days, yellow < 30 days, green otherwise)
- "Mark as Filed" button per row
- "Setup Reminders" button per corporation (calls `setup-reminders` endpoint, creates scheduler entries)
- "Prepare Nil T2" link for T2 rows (navigates to NilT2Page)

**`CorporationPage`** shows:
- Form: all Corporation fields + save/update
- After save: display computed next filing dates for all 3 types

**`NilT2Page`** shows:
- Select corporation + fiscal year
- Two toggles: "Had any income?" / "Had any expenses?" — if both No, enable generate button
- Generated report rendered as a clean printable summary: Identification block, Schedule 100, Schedule 125, Schedule 1 (all showing nil/zero values pre-filled with corp details)
- "Print / Save as PDF" button (browser print)

---

## Infrastructure Changes

### `docker-compose.yml`
Add service:
```yaml
tax-backend:
  build:
    context: ./backends/tax-py
  container_name: tax-backend
  environment:
    - TAX_DATABASE_URL=sqlite:////data/tax.db
    - SCHEDULER_API_URL=http://scheduler-backend:8000
  command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007", "--reload"]
  volumes:
    - ./backends/tax-py/app:/app/app
    - tax_db:/data
  ports:
    - '8007:8007'
  depends_on:
    - scheduler-backend
```
Add `tax_db:` to volumes section.
Also add `tax-backend` to `apps-frontend.depends_on`.

### `vite.config.ts`
Add:
```ts
const taxTarget = process.env.TAX_API_PROXY_TARGET ?? 'http://localhost:8007'
// in proxy:
'/tax-api': { target: taxTarget, changeOrigin: true, rewrite: path => path.replace(/^\/tax-api/, '') }
```

### `docker-compose.yml` (frontend env)
Add to `apps-frontend.environment`:
```yaml
- VITE_TAX_API_BASE=/tax-api
- TAX_API_PROXY_TARGET=http://tax-backend:8007
```

### `App.tsx`
Add imports + routes:
```tsx
import { CorporationPage } from "./features/tax/CorporationPage";
import { TaxDashboardPage } from "./features/tax/TaxDashboardPage";
import { NilT2Page } from "./features/tax/NilT2Page";
// routes:
<Route path="tax/corporations" element={<CorporationPage />} />
<Route path="tax/dashboard" element={<TaxDashboardPage />} />
<Route path="tax/nil-t2" element={<NilT2Page />} />
```

### `featureNavigation.ts`
Add new nav group:
```ts
{
  id: "tax",
  label: "Tax",
  description: "Corporate tax filing reminders and preparation",
  items: [
    { path: "/tax/corporations", label: "Corporations", description: "Manage corporation profiles and details", keywords: ["tax", "corporation", "profile", "corp"] },
    { path: "/tax/dashboard", label: "Tax Deadlines", description: "Upcoming filing deadlines with scheduler reminders", keywords: ["tax", "deadline", "annual return", "gst", "hst", "t2", "reminder"], quickAccess: true },
    { path: "/tax/nil-t2", label: "Nil T2 Report", description: "Generate a nil T2 return for zero-income corporations", keywords: ["t2", "nil", "zero income", "corporate tax", "cra"] },
  ],
}
```

---

## Files to Create
1. `backends/tax-py/Dockerfile`
2. `backends/tax-py/requirements.txt`
3. `backends/tax-py/app/__init__.py`
4. `backends/tax-py/app/database.py`
5. `backends/tax-py/app/models.py`
6. `backends/tax-py/app/schemas.py`
7. `backends/tax-py/app/crud.py`
8. `backends/tax-py/app/tax_dates.py`
9. `backends/tax-py/app/nil_t2.py`
10. `backends/tax-py/app/main.py`
11. `frontends/customer-portal/src/api/tax.ts`
12. `frontends/customer-portal/src/features/tax/types.ts`
13. `frontends/customer-portal/src/features/tax/CorporationPage.tsx`
14. `frontends/customer-portal/src/features/tax/TaxDashboardPage.tsx`
15. `frontends/customer-portal/src/features/tax/NilT2Page.tsx`

## Files to Modify
1. `docker-compose.yml` — add tax-backend service + volume
2. `frontends/customer-portal/vite.config.ts` — add tax-api proxy
3. `frontends/customer-portal/src/App.tsx` — add tax routes
4. `frontends/customer-portal/src/config/featureNavigation.ts` — add Tax nav group

---

## Verification

1. `docker-compose up --build tax-backend` — confirm service starts on port 8007, tables created
2. `curl http://localhost:8007/` → `{"status":"ok"}`
3. POST a corporation via curl, verify DB record
4. GET `/corporations/{id}/filing-schedule` → confirm correct due dates for Annual Return, GST/HST quarters, and T2
5. POST `/corporations/{id}/setup-reminders` → confirm events+reminders appear in scheduler at `http://localhost:8000/events` for all 3 filing types
6. Open `http://localhost:5173/tax/dashboard` → see all upcoming deadlines including T2, "Setup Reminders" button, "Mark as Filed" button, "Prepare Nil T2" link
7. Open `http://localhost:5173/tax/corporations` → create/edit corporation form works, computed dates shown for all 3 types
8. Open `http://localhost:5173/tax/nil-t2` → select corp + fiscal year, toggle no income/no expenses, generate report, verify CRA schedule fields populated with corp details
9. Verify "Print / Save as PDF" triggers browser print dialog
10. Verify new "Tax" group (3 items) appears in sidebar nav with search working

## Out of Scope (Next Phase)
- Direct CRA NETFILE submission
- T2 preparation for corporations with income or expenses (accountant required)
- Email/push notification delivery for reminders (today reminders are stored data only)

---

## Parked: Accountant Scaling + Individual Taxpayers (Future Plan)

*Full discussion captured — to be planned separately.*

### Individual Taxpayers
- New entity type: personal profile (SIN, marital status, dependents)
- Slip uploads: T4, T4A, T5, T3, T2202
- **T4 PDF parsing** via `pdfplumber` — extract CRA box values (Box 14, 22, 16, 18, etc.) automatically; accountant gets structured data, never re-types a T4
- Annual tax questionnaire (RRSP, medical, donations, childcare, home office)
- Deadlines: T1 April 30 (June 15 self-employed), RRSP March 1 — reminders at 60/30/14/7 days

### Accountant Scaling Tools
- All-clients deadline dashboard (control tower view across all corp + individual clients)
- Outstanding items tracker + one-click nudge
- Filing status tracker: Waiting for docs → In progress → Filed → CRA confirmed
- Annual questionnaire (per client, triggered by accountant)
- Document vault (organized by client + tax year)
- Lead intake page (shareable link, structured form → pipeline)
- Simple CRM pipeline: New → Contacted → Proposal → Active
- Public free tool (deadline checker, no login) as lead magnet — captures email
- Referral tracking from existing clients
- Accountant public profile page (services, pricing, booking link)
- Pre-filled data export for licensed tax filing software (PDF/structured summary)
- User roles: `accountant` (admin) / `corporation_client` / `individual_client`

### Notification + Communication Service (`comms-py`)
- Delivery priority (cheapest first): in-app → email (SendGrid free / self-hosted SMTP) → WhatsApp → SMS (Twilio, deferred)
- **WhatsApp:** Meta Cloud API official — 1,000 free conversations/month
- Two-way: outbound reminders + inbound replies routed to chatbot
- Keyword shortcuts: "FILED" marks filing done, "HELP" returns FAQ list (no AI cost)

### RAG Chatbot (`chatbot-rag-py`)
- Accountant manages knowledge base (FAQs, policies, tax guides) via dashboard
- Stack (all open source / zero ongoing cost):
  - Embeddings: `sentence-transformers` all-MiniLM-L6-v2 (runs in Docker, free)
  - Vector store: ChromaDB (Docker service, free)
  - LLM: Ollama + Llama 3.2 (runs locally, free — needs ~8GB RAM on server)
  - Fallback if Ollama quality insufficient: Claude Haiku with prompt caching (~$0.25/1M cached tokens)
  - Framework: LangChain (open source)
- Retrieval flow: embed question → top-k chunks from ChromaDB → LLM generates response
- Ollama runs entirely within Docker network — no data leaves the server

### Security Requirements (applies to all phases)
- AES-256 encryption at rest for SIN and Business Number fields
- Audit log: who accessed what document/record, when
- PIPEDA compliance (Canadian privacy law) — data retention policy
- Role-based access: clients can only see their own data
- WhatsApp messages handled in-memory + audit log only
