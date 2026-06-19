# Getting Started

This guide helps you set up the project and start experimenting with the services.

---

## Prerequisites

Install these before you begin:

- **Docker Desktop** — [download here](https://www.docker.com/products/docker-desktop/) — runs all services and databases
- **Node.js 18+** — only needed if you want to run the frontend outside Docker
- **Python 3.11+** — only needed if you want to run a Python backend outside Docker
- **Go 1.22+** — only needed if you want to run a Go backend outside Docker

Check versions:
```bash
docker --version       # Docker version 24+
node --version         # v18+
python3 --version      # 3.11+
go version             # go1.22+
```

---

## Option 1: Run Everything with Docker (Recommended)

The easiest way to start. One command brings up all services and databases.

```bash
# From the project root
docker compose up --build
```

Wait about 60–90 seconds for all services to start. Then open:
- **Frontend:** http://localhost:5173
- **Any service's API docs:** http://localhost:<port>/docs (e.g., http://localhost:8005/docs for auth)

**Login credentials:**
| Username | Password |
|----------|----------|
| `demo` | `demo123` |
| `admin` | `admin123` |
| `user` | `user123` |

### Useful Docker commands
```bash
# See what's running
docker compose ps

# View logs for a specific service
docker compose logs -f auth-backend
docker compose logs -f todo-backend

# Stop everything
docker compose down

# Stop and remove volumes (wipes databases)
docker compose down -v
```

---

## Option 2: Run One Service Locally

Useful when you're working on a specific service and want fast hot-reload.

### Step 1 — Start only the databases

```bash
# Start only the infrastructure (no app services)
docker compose up -d postgres redis mongo kafka zookeeper
```

### Step 2 — Run the service you want

**Python services (FastAPI):**
```bash
cd backends/auth-py
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

```bash
cd backends/scheduler-py
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
cd backends/chatbot-py
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

**Go services:**
```bash
cd backends/todo-go
go run ./cmd/server
```

```bash
cd backends/chatbot-go
PORT=8004 go run ./cmd/server
```

**Frontend:**
```bash
cd frontends/customer-portal
npm install
npm run dev
```

### VS Code Tasks

If you use VS Code, all services have pre-configured tasks under **Terminal → Run Task**. Look for `Local Run: <ServiceName>`.

---

## Explore the API Docs

Every FastAPI backend has interactive API docs at `/docs`:

| Service | URL |
|---------|-----|
| Auth | http://localhost:8005/docs |
| Scheduler | http://localhost:7001/docs |
| Finance | http://localhost:8001/docs |
| Validator | http://localhost:8002/docs |
| Chatbot (Python) | http://localhost:8003/docs |
| Marketplace | http://localhost:8006/docs |
| Tax | http://localhost:8007/docs |
| Agentic Chat | http://localhost:8010/docs |

Go backends expose health checks at `/healthz`.

---

## Try the Marketplace (Kafka Demo)

The marketplace demonstrates event-driven architecture end-to-end.

1. Start services: `docker compose up -d kafka zookeeper marketplace-api payment-consumer frontend`
2. Log in at http://localhost:5173 with `demo` / `demo123`
3. Click **Marketplace** in the sidebar
4. Create an order (any User ID, any amount)
5. Check that the payment consumer processed it:
   ```bash
   docker compose logs payment-consumer | grep "Created payment"
   ```

---

## Environment Variables

Services are configured via environment variables. The defaults in `docker-compose.yml` work out of the box. If you run a service locally, the key variables are:

| Variable | Service | Default |
|----------|---------|---------|
| `DATABASE_URL` | auth, scheduler, todo, tax | set in docker-compose.yml |
| `AUTH_SECRET_KEY` | auth | change this in production |
| `KAFKA_BOOTSTRAP` | marketplace | `localhost:19100` (local) / `kafka:9092` (Docker) |
| `REDIS_URL` | auth, agentic-chat | `redis://localhost:6100` |
| `ANTHROPIC_API_KEY` | agentic-chat | required if using agentic chat |

---

## Troubleshooting

**Port already in use:**
```bash
# Find what's using port 5173
lsof -i :5173
```

**Database not ready yet:**
Services retry on startup. If a service crashes immediately, wait 10 seconds and run:
```bash
docker compose restart <service-name>
```

**Frontend shows blank page after login:**
Clear `localStorage` in your browser's developer tools, then log in again.

**Kafka consumer not receiving events:**
Confirm Kafka is healthy first:
```bash
docker compose ps kafka
# Should show "healthy"
```

---

## Next Steps

- Browse the services through the UI at http://localhost:5173
- Read the per-service docs in [`docs/`](docs/README.md)
- Modify a backend and watch hot-reload update it instantly
- Try adding a new endpoint to an existing service
