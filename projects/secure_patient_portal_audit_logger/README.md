# Secure Patient Portal Authentication & Audit Logger — Case Study

A case study for a HIPAA-conscious patient-portal authentication flow with an
**immutable, write-once audit trail** — designed to be exercised end-to-end
locally using [Floci](https://github.com/) before any production
infrastructure is written.

> **Status:** Architecture case study (design + rationale). No runnable code in
> this folder.

---

## Domain

Medical & Healthcare IT — secure patient access and compliance auditing of
Protected Health Information (PHI).

## Architecture

```
   Patient
     │  login
     ▼
 ┌─────────┐     ┌──────────────┐     ┌────────────┐
 │ Cognito │ ──► │ API Gateway  │ ──► │ DynamoDB   │  (audit table)
 │  User   │     │ (history req)│     │   row      │
 │  Pools  │     └──────────────┘     └─────┬──────┘
 └─────────┘                                │ DynamoDB Stream
                                            ▼
                                      ┌───────────┐     ┌─────────────┐
                                      │  Lambda   │ ──► │  S3 (WORM)  │
                                      │ archiver  │     │ immutable   │
                                      └───────────┘     │ audit log   │
                                                        └─────────────┘
```

## Flow

1. A patient authenticates via **Amazon Cognito User Pools**.
2. On success, they request their medical history through **API Gateway**, which
   writes an access row into a **DynamoDB** audit table.
3. A **DynamoDB Stream** captures that access event immediately and triggers a
   **Lambda** function.
4. The Lambda archives the immutable access log into a write-once (WORM) **S3**
   bucket for strict compliance auditing.

## Why run it locally with Floci

Security and audit trails are paramount in medical tech, and orchestrating
Cognito, API Gateway tokens, and DynamoDB Streams together is traditionally hard
without a live AWS environment. Floci lets you test the **end-to-end security
handshake** and verify that the immutable audit trail fires flawlessly —
before writing a single line of production infrastructure code.

## Key engineering challenges to explore

- Cognito token issuance and verification at the API Gateway boundary.
- Guaranteeing the audit write happens on **every** history access (no bypass).
- DynamoDB Streams → Lambda delivery semantics (at-least-once, ordering).
- Enforcing write-once / immutability on the S3 audit bucket (object lock).
- Proving the audit trail is complete and tamper-evident.
