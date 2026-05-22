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
pip install -r projects/real_time_fraud_detector/src/requirements.txt
pip install -r projects/automated_phr_pipeline/src/requirements.txt
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

| Project | Domain | Tech Stack | Description |
| :--- | :--- | :--- | :--- |
| [`real_time_fraud_detector`](./projects/real_time_fraud_detector/) | Fintech / Banking | API Gateway, SQS, Lambda, ElastiCache (Redis) | High-throughput velocity and fraud checking for card transactions. |
| [`automated_phr_pipeline`](./projects/automated_phr_pipeline/) | Healthcare IT | S3, AWS Lambda, RDS PostgreSQL, Floci | HIPAA-compliant health record ingestion and schema validation. |
| [`open_banking_analytics`](./projects/open_banking_analytics/) | Fintech / Analytics | S3, Glue Catalog, Athena (via DuckDB) | Analytical engine for querying mock open-banking data lakes entirely offline. |
| [`floci_demo`](./projects/floci_demo/) | Cloud Emulation / DevTools | Floci, S3, SQS, DynamoDB, Streamlit | Document-processing pipeline demo running a full S3 + SQS + DynamoDB workflow locally via Floci. |
| [`agent_prompting`](./projects/agent_prompting/) | AI / LLM | Python | Agent prompting patterns and prompt-engineering utilities. |
| [`ansible_docker_automation`](./projects/ansible_docker_automation/) | DevOps / Automation | Ansible, Docker | Ansible playbooks to build Docker images, deploy containers, and run smoke tests. |
| [`aws_sagemaker`](./projects/aws_sagemaker/) | AI / MLOps | AWS SageMaker, Jupyter | Notebook to deploy Falcon-40B Instruct on SageMaker. |
| [`caching_projects`](./projects/caching_projects/) | Backend / Databases | Python, Redis, MongoDB, PostgreSQL | Duplicate-entry checks and server-side read-through caching with Redis. |
| [`crewAI_SQLite3_Flask`](./projects/crewAI_SQLite3_Flask/) | AI / Backend | CrewAI, Flask, SQLite | Multi-agent CrewAI workflow exposed through a Flask REST API backed by SQLite. |
| [`develop_fine_tuned_model_interface`](./projects/develop_fine_tuned_model_interface/) | AI / Backend | Flask, Python | Minimal Flask service for serving a fine-tuned text-generation model via REST. |
| [`docker_alone`](./projects/docker_alone/) | DevOps / Containers | Docker | Bare-minimum Dockerfile scaffold — single-container setup without Compose. |
| [`docker_compose`](./projects/docker_compose/) | DevOps / Containers | Docker, Docker Compose, Kafka | Multi-service Compose reference with Kafka stack and the YAML anchor reuse pattern. |
| [`docker_debugger`](./projects/docker_debugger/) | DevOps / Containers | Docker, Docker Compose, VS Code | Scaffold for attaching a VS Code debugger to a containerized service. |
| [`docker_entrypoint`](./projects/docker_entrypoint/) | DevOps / Containers | Docker, Node.js | ENTRYPOINT + CMD pattern: shell readiness script that execs a Node app. |
| [`docker_entrypoint_compose_2`](./projects/docker_entrypoint_compose_2/) | DevOps / Containers | Docker, Docker Compose, Python | ENTRYPOINT pattern with Compose and a Python service variant. |
| [`flask_streamlit_langchain`](./projects/flask_streamlit_langchain/) | AI / Full-stack | Flask, SQLAlchemy, Streamlit, LangChain | Flask CRUD API (SQLite) with a Streamlit UI and LangChain NL query scaffold. |
| [`fullstack_go_project`](./projects/fullstack_go_project/) | Full-stack | Go, React, Docker, Kubernetes | Production-style full-stack app with Go backend, React frontend, and K8s manifests. |
| [`fullstack_websocket`](./projects/fullstack_websocket/) | Full-stack | Python, WebSocket, React | Real-time full-stack app using WebSockets between a Python backend and React frontend. |
| [`go_websocket_and_api_calls`](./projects/go_websocket_and_api_calls/) | Backend / Networking | Go | Go client/server pairs demonstrating WebSocket and REST API call patterns. |
| [`kafka_kafdrop_ui_project`](./projects/kafka_kafdrop_ui_project/) | Backend / Streaming | Kafka, Kafdrop, Python, Docker | Dockerized Kafka stack with Kafdrop UI and a Python producer/consumer. |
| [`kubernetes_project`](./projects/kubernetes_project/) | DevOps / Kubernetes | Kubernetes, Python, Streamlit, MongoDB | K8s manifests and a full Python + Streamlit + MongoDB Todo app deployed on Kubernetes. |
| [`kubernetes_voting_app`](./projects/kubernetes_voting_app/) | DevOps / Kubernetes | Kubernetes, Redis, PostgreSQL | Classic voting app fully deployed on Kubernetes across 5 services. |
| [`langchain_conversation_memory_projects`](./projects/langchain_conversation_memory_projects/) | AI / LLM | LangChain, OpenAI | Side-by-side comparison of 4 LangChain conversation memory types. |
| [`langchain_rag_app`](./projects/langchain_rag_app/) | AI / LLM | LangChain, OpenAI, FAISS | End-to-end RAG pipeline: load text → embed → FAISS vector store → conversational retrieval. |
| [`langgraph_multiagents`](./projects/langgraph_multiagents/) | AI / LLM | LangGraph, Python | LangGraph-based multi-agent agentic workflow implementation. |
| [`llama_streamlit_chatbot_interface`](./projects/llama_streamlit_chatbot_interface/) | AI / LLM | Llama 2, Streamlit, LangChain, FAISS | Local Llama 2 chatbot: upload a CSV, build embeddings, and chat with it via Streamlit. |
| [`loadbalance_caddy`](./projects/loadbalance_caddy/) | DevOps / Networking | Caddy, Docker | Load balancing two HTML servers with Caddy run via Docker containers. |
| [`loadbalance_custom_network`](./projects/loadbalance_custom_network/) | DevOps / Networking | Docker | Load balancing demo using Docker custom bridge networks. |
| [`loadbalance_roundrobin_config`](./projects/loadbalance_roundrobin_config/) | DevOps / Networking | Caddy, Docker Compose | Full round-robin load balancer with Caddy and Docker Compose. |
| [`mongo_orm_structure`](./projects/mongo_orm_structure/) | Backend / Databases | MongoDB, MongoEngine, Marshmallow | ODM layer using MongoEngine + Marshmallow dataclasses for a chatbot message domain. |
| [`mongodb_caching`](./projects/mongodb_caching/) | Backend / Databases | MongoDB, Python | MongoDB-backed response cache keyed by SHA-256 hash with TTL expiry. |
| [`mongodb_distributed_lock`](./projects/mongodb_distributed_lock/) | Backend / Databases | MongoDB, Python | Distributed lock implementation using MongoDB with TTL-based auto-release. |
| [`mongodb_to_avoid_duplicate`](./projects/mongodb_to_avoid_duplicate/) | Backend / Databases | MongoDB, Python | CacheManager combining response caching, duplicate-request detection, and distributed lock. |
| [`parallel_chain_function_calling`](./projects/parallel_chain_function_calling/) | AI / LLM | LangChain, FastAPI, OpenAI | Parallel self-correcting LangChain tool-calling chain with retry/fallback, served via FastAPI. |
| [`pdf_rag_chatbot`](./projects/pdf_rag_chatbot/) | AI / LLM | RAG, Streamlit, Python | RAG chatbot over PDFs with a Streamlit UI and database-backed vector store. |
| [`pgvector_rag`](./projects/pgvector_rag/) | AI / LLM | PostgreSQL, pgvector, LangChain, OpenAI | RAG with pgvector: embed documents and run similarity search against Postgres. |
| [`pgvectorscale_rag_solution`](./projects/pgvectorscale_rag_solution/) | AI / LLM | PostgreSQL, pgvectorscale, LangChain, Docker | Production-oriented RAG solution using pgvectorscale for ANN search at scale. |
| [`pod_health_check_logics`](./projects/pod_health_check_logics/) | DevOps / Kubernetes | Python (stdlib) | HTTP health-check server for Kubernetes liveness/readiness probes, zero dependencies. |
| [`python_websocket_and_api_calls`](./projects/python_websocket_and_api_calls/) | Backend / Networking | FastAPI, WebSocket, Python | Three matched server/client pairs: REST+WebSocket (JSON), XML, and XML+Pydantic validation. |
| [`rag_from_scratch_project_1`](./projects/rag_from_scratch_project_1/) | AI / LLM | Python, Jupyter | Notebook series building a RAG system from scratch across 18 steps. |
| [`streamlit_kafka`](./projects/streamlit_kafka/) | Backend / Streaming | Streamlit, Kafka, Python | Streamlit UI for producing custom-structured dummy metric data into a Kafka topic. |
| [`podman_docker_kubernetes`](./projects/podman_docker_kubernetes/) | DevOps / Containers | Podman, Docker, Kubernetes | Podman-based container workflows and Kubernetes deployment patterns. |
| [`voicebox_agent`](./projects/voicebox_agent/) | AI / Voice | Python, Voicebox, MCP | Local voice notifications for CLI pipelines and AI agents using the Voicebox REST API. |


## ⚠️ Disclaimer

The projects in this repository are intended for educational purposes, local development prototyping, and architectural demonstrations. While they simulate real-world domains (like fintech and healthcare), they are not production-ready out of the box and should be thoroughly audited and secured before any real-world deployment.
