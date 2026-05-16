# 📦 Public Projects

Welcome to my central engineering hub. This repository serves as an open-source portfolio and playground for my personal projects, architectural prototypes, and system experiments.

The goal here is to showcase production-grade architectures across multiple engineering domains—ranging from AI-native systems and cloud emulations to low-level networking and full-stack applications—all designed with a clean, modular, and self-contained philosophy.

---

## 🚀 Repository Philosophy

* **100% Independent:** Every project lives in its own directory with isolated source code and environment configuration. Runtime dependencies (Python venv, Node modules) are managed at the repo root to avoid duplication — see the [Dependency Management](#-dependency-management) section.
* **Production-Grade Patterns:** Even when running in a local or simulated environment, the projects implement real-world enterprise patterns (e.g., event-driven loops, strict data validation, secure auth handshakes).
* **Plug & Play:** Each project includes clear initialization scripts, Docker configurations, or setup guides so you can spin them up and explore the code instantly.

---

## 🗂️ Project Directory

See the **Projects** table below.

---

## 🛠️ Getting Started

### Prerequisites
Before running any of the projects, ensure you have the following installed:
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine
* [Miniconda](https://docs.conda.io/en/latest/miniconda.html) with Python 3.12+ (for Python projects)
* Node.js 24+ and npm 11+ via [nvm](https://github.com/nvm-sh/nvm) (for Node/React projects)
* Go 1.26+ (for Go projects)

### How to Run a Project
**Clone the repository:**
```bash
git clone https://github.com/fullstackfusions/public_projects.git
cd public_projects
```

Set up root-level dependencies once (see [Dependency Management](#-dependency-management) below), then navigate into any `projects/<name>/` directory and follow its own `README.md`.

---

## 📦 Dependency Management

To avoid duplicating large dependency trees (Python venvs, `node_modules`) across every project, all runtime dependencies are managed **at the repo root**.

### Python
This repo uses **Miniconda** to manage Python. The `base` conda environment (Python 3.12) is shared across all Python projects:
```bash
# Ensure conda base is active and on PATH
conda activate base
python3 --version   # should show 3.12.x

# Install deps for any/all Python projects
pip install -r projects/1.real-time-fraud-detector/src/requirements.txt
pip install -r projects/2.automated-phr-pipeline/src/requirements.txt
```
> Each project's `README.md` lists its specific `pip install` command. Always run `conda activate base` before working on any Python project.
>
> If two projects require conflicting package versions, that project's `README.md` will document a dedicated `conda create -n <project> python=3.12` environment instead.

### Node / React
A root `package.json` uses [npm workspaces](https://docs.npmjs.com/cli/using-npm/workspaces) to manage all JS projects from one `node_modules/`:
```bash
# Install all workspace deps from repo root
npm install
```
Each Node/React project under `projects/` is declared as a workspace and keeps its own `package.json` for deps and scripts.

### Go
No setup needed at the root level. Go caches modules in `$GOPATH/pkg/mod` globally. Each Go project has its own `go.mod`/`go.sum` — just run `go run ./...` or `go build` inside the project directory.

> **Note:** The shared Python venv works well as long as projects don't require conflicting package versions. If a conflict arises, that project's `README.md` will document a per-project venv exception.

### Projects

| # | Project Name | Domain | Tech Stack | Description |
| :-: | :--- | :--- | :--- | :--- |
| **1** | [`real-time-fraud-detector`](./projects/1.real-time-fraud-detector/) | Fintech / Banking | API Gateway, SQS, Lambda, ElastiCache (Redis) | High-throughput velocity and fraud checking for card transactions. |
| **2** | [`automated-phr-pipeline`](./projects/2.automated-phr-pipeline/) | Healthcare IT | S3, AWS Lambda, RDS PostgreSQL, Floci | HIPAA-compliant health record ingestion and schema validation. |
| **3** | [`open-banking-analytics`](./projects/3.open-banking-analytics/) | Fintech / Analytics | S3, Glue Catalog, Athena (via DuckDB) | Analytical engine for querying mock open-banking data lakes entirely offline. |


## ⚠️ Disclaimer

The projects in this repository are intended for educational purposes, local development prototyping, and architectural demonstrations. While they simulate real-world domains (like fintech and healthcare), they are not production-ready out of the box and should be thoroughly audited and secured before any real-world deployment.
