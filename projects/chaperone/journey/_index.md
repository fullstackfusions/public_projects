---
title: "Chaperone Hackathon Journey — Index"
---

# Chaperone — the hackathon journey

A running record of building [Chaperone](../README.md) for the AWS Zero to Shipped Hackathon. It records the moments, the decisions and the reasoning behind them, the hands-on console work, and how Claude Code on the `hermes` VPS used the AWS MCP Server to build it.

> **Status:** Days 0–1 are published. The code in this folder is refreshed daily; the journey for the remaining days is updated once, at submission.

## How this folder is kept

- **One day file per working day** (`YYYY-MM-DD-dayN.md`): a timestamped timeline of what happened, with the exact commands or MCP scripts, what was surprising, and a **Video beat** note on how to show it on screen.
- **[decisions](decisions.md)**: every decision with the options considered, the choice, and why. Append-only; a reversed decision gets a new entry that points at the old one.
- **[gotchas](gotchas.md)**: surprises and traps (console defaults that cost money, confusing CloudTrail views, AWS MCP behaviour).
- **`assets/<date>/`**: screenshots, numbered in order. Only screenshots that show no account ID, email, IP, portal URL or account ARN are published; the day files say which ones are left out.
- CloudTrail is the source of truth for timestamps of anything the agent did. Chaperone itself will replay these sessions, so the video can use Chaperone's own timeline as B-roll.

## Diagrams

- [architecture-phases](architecture-phases.md): six Eraser diagram-as-code blocks, phase 0 (account hardening) to phase 5 (target architecture), for showing in the video how the design grew

## Days

- [Day 0 — Thu Sep 24 (into Fri Sep 25 UTC)](2026-09-24-day0.md): picking the idea, AWS account hardening, CloudTrail, the agent's own identity, AWS MCP Server on the VPS, the three-level attribution discovery, hello-world live on CloudFront
- [Day 1 — Fri Sep 25](2026-09-25-day1.md): the agent signs in again, Terraform state in S3, Day 0 adopted into Terraform with zero changes, then the ingest pipeline, every region, least privilege against IAM Access Analyzer, and the MCP server

## Where things live

| What | Where |
|---|---|
| How it works | [docs/architecture.md](../docs/architecture.md) |
| Code | [backend/](../backend/), [mcp/](../mcp/), [infra/](../infra/) in this folder |
| Live demo | https://chaperone.fullstackfusions.com |

## Related

- [Chaperone README](../README.md) · [Architecture](../docs/architecture.md)
- [decisions](decisions.md) · [gotchas](gotchas.md)
