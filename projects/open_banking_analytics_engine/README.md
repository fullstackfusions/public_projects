# Open Banking Financial Analytics Engine — Case Study

A case study for an internal analytics engine that ingests raw third-party
banking transaction logs and serves personalized spending insights — designed
to run **entirely offline** on a laptop using [Floci](https://github.com/)'s
DuckDB-powered Athena sidecar.

> **Status:** Architecture case study (design + rationale). No runnable code in
> this folder — see [`open_banking_analytics`](../open_banking_analytics/) for a
> working implementation in the same domain.

---

## Domain

Fintech / Personal Banking — analytical querying over large mock open-banking
data lakes.

## Architecture

```
Third-party banking APIs
        │  (CSV / Parquet transaction logs)
        ▼
      ┌─────┐      ┌───────────────┐      ┌──────────────────────────┐
      │ S3  │ ───► │ Glue Catalog  │ ───► │ Athena (DuckDB sidecar)  │
      └─────┘      └───────────────┘      └──────────────────────────┘
   raw object       schema / table          analytical SQL queries
     storage         definitions         (window functions, aggregates)
                                                    │
                                                    ▼
                                       Personalized user dashboards
                                  (monthly trends, merchant categories,
                                        average balances)
```

## Flow

1. Thousands of raw transaction logs (CSV/Parquet) from third-party banking APIs
   land in an **S3** bucket.
2. A **Glue Data Catalog** defines the schema over those objects, exposing them
   as queryable tables.
3. An analytical service runs **Athena** SQL to compute:
   - monthly spending trends,
   - merchant-category breakdowns,
   - average balances,
   for personalized user dashboards.

## Why run it locally with Floci

Financial reporting is dominated by heavy SQL analytical workloads. Floci's
native **DuckDB-powered Athena sidecar** lets you test complex window functions
and financial aggregation queries locally on your hard drive — scanning
gigabytes of mock financial records instantly and for free, with no cloud cost.

## Key engineering challenges to explore

- Window functions for rolling balances and month-over-month spend deltas.
- Partitioning strategy in S3 (e.g. by `year/month/user`) and its effect on
  scan cost.
- Schema evolution in the Glue Catalog as upstream banking-API formats change.
- Validating aggregation correctness against a known fixture dataset.
