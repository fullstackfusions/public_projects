# Marketplace Demo - Contract-First Event-Driven Architecture

A minimal demonstration of modern microservices architecture using:
- **FastAPI** (Python backend)
- **React** (TypeScript frontend)
- **Kafka/Confluent Kafka** (Event streaming)

## 🎯 Key Concepts Demonstrated

### 1. **OpenAPI - HTTP Contract**
FastAPI auto-generates OpenAPI specification at `/docs` and `/openapi.json`.
- Type-safe API contracts
- Interactive documentation
- Client code generation ready

### 2. **AsyncAPI - Event Contract**
Event schemas defined in `asyncapi.yaml` and enforced with Pydantic.
- Versioned event schemas (e.g., `OrderCreatedEventV1`)
- Producer/consumer contract validation
- Schema evolution strategy

### 3. **Routing via Topics**
Events routed by Kafka topic names (e.g., `orders.created`), NOT flags in payload.
- Clean event semantics
- Topic-level access control
- Independent retention policies

### 4. **Consumer Groups - Scaling Units**
Each service uses a consumer group ID for horizontal scaling.
- `payment-service-v1` = scaling unit for payment service
- Multiple instances share load within same group
- Fault tolerance and load distribution

### 5. **Data Contracts - Data Ownership**
Services own their data, integrate via APIs/events.
- `marketplace-api` owns orders (OpenAPI)
- `payment-service` owns payments (AsyncAPI consumer)
- NO shared ORM or database

## 🏗️ Architecture

```
┌─────────────┐
│   React UI  │
│  (port 5173)│
└──────┬──────┘
       │ HTTP (OpenAPI)
       │ POST /orders
       ▼
┌─────────────────┐
│ Marketplace API │
│   (port 8006)   │
└────────┬────────┘
         │ Publish Event
         │ Topic: orders.created
         │ (AsyncAPI contract)
         ▼
┌─────────────────┐
│     Confluent Kafka    │
│   Kafka-compat  │
│  (port 19092)   │
└────────┬────────┘
         │ Consumer Group: payment-service-v1
         │ (Horizontal scaling)
         ▼
┌─────────────────┐
│ Payment Consumer│ ──> payments.db (SQLite)
│  (background)   │
└─────────────────┘
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start all services (Confluent Kafka + API + Consumer + Frontend)
docker-compose up -d

# View logs
docker-compose logs -f marketplace-api payment-consumer

# Stop all
docker-compose down
```

**URLs**:
- Frontend: http://localhost:5173/marketplace
- Marketplace API: http://localhost:8006/docs

**🔐 Login Required**: Use `demo` / `demo123` (or see [LOGIN_CREDENTIALS.md](../../LOGIN_CREDENTIALS.md))
docker-compose logs -f marketplace-api payment-consumer

# Stop all
docker-compose down
```

**URLs**:
- Frontend: http://localhost:5173/marketplace
- Marketplace API: http://localhost:8006/docs

### Option 2: Local Development

**Prerequisites**: Python 3.11+, Node.js 18+

```bash
# 1. Start Kafka (Confluent)
docker-compose up -d kafka

# 2. Install Python dependencies
pip install -r backends/marketplace-py/requirements.txt
pip install -r backends/marketplace-py/consumer/requirements.txt

# 3. Start Marketplace API
cd backends/marketplace-py
KAFKA_BOOTSTRAP=localhost:19092 uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload

# 4. Start Payment Consumer (in another terminal)
cd backends/marketplace-py/consumer
KAFKA_BOOTSTRAP=localhost:19092 KAFKA_GROUP_ID=payment-service-v1 python payment_consumer.py

# 5. Start Frontend (in another terminal)
cd frontends/customer-portal
npm install
npm run dev
```

**Or use VS Code tasks**:
- `Docker: Start Confluent Kafka Only`
- `Local Run: Marketplace API`
- `Local Run: Payment Consumer`
- `Local Run: Frontend`

## 📝 API Contract (OpenAPI)

### Create Order
```http
POST http://localhost:8006/orders
Content-Type: application/json

{
  "user_id": "user_1",
  "amount_cents": 1999
}
```

**Response**:
```json
{
  "order_id": "ord_user_1_1999",
  "status": "created"
}
```

**Interactive docs**: http://localhost:8006/docs

## 📡 Event Contract (AsyncAPI)

### OrderCreatedEventV1

**Topic**: `orders.created`

**Payload**:
```json
{
  "order": {
    "order_id": "ord_user_1_1999",
    "user_id": "user_1",
    "amount_cents": 1999
  }
}
```

**Specification**: [`asyncapi.yaml`](asyncapi.yaml)

**Validation**: Pydantic schema in both producer and consumer

## 🔄 Event Flow

1. User creates order in React UI
2. React calls `POST /orders` (OpenAPI contract)
3. Marketplace API validates request with Pydantic
4. API creates order and publishes `OrderCreatedEventV1` to Kafka topic `orders.created`
5. Payment consumer (group `payment-service-v1`) receives event
6. Consumer validates event against Pydantic schema (AsyncAPI contract)
7. Consumer creates payment in local database (`payments.db`)
8. React receives immediate order confirmation

## 📊 Data Ownership

| Domain   | Owner              | Storage         | Integration         |
|----------|-------------------|-----------------|---------------------|
| Orders   | marketplace-api   | (in-memory)     | HTTP API + Events   |
| Payments | payment-consumer  | payments.db     | Events only         |

**No shared database or ORM**. Services integrate via:
- HTTP APIs (synchronous) - OpenAPI contract
- Kafka events (asynchronous) - AsyncAPI contract

## 🎚️ Horizontal Scaling

### Scale Payment Service

Run multiple instances with same `KAFKA_GROUP_ID`:

```bash
# Terminal 1
KAFKA_BOOTSTRAP=localhost:19092 KAFKA_GROUP_ID=payment-service-v1 python payment_consumer.py

# Terminal 2
KAFKA_BOOTSTRAP=localhost:19092 KAFKA_GROUP_ID=payment-service-v1 python payment_consumer.py

# Kafka distributes partitions across both instances
```

### Add New Consumer Service

Create notification service (example):

```python
# notification_consumer.py
consumer = AIOKafkaConsumer(
    "orders.created",
    group_id="notification-service-v1",  # Different group = independent scaling
    # ...
)
```

Both payment and notification services consume same topic but scale independently.

## 🧪 Testing the Flow

1. Open React UI: http://localhost:5173/marketplace
2. Fill in User ID: `user_1`
3. Set Amount: `1999` cents ($19.99)
4. Click "Create Order"
5. Check payment consumer logs:
   ```
   💳 Created payment pay_abc123 for order ord_user_1_1999 ($19.99)
   ```

## 📂 Project Structure

```
backends/
  marketplace-py/              # Marketplace API service
    app/
      main.py                  # FastAPI app + OpenAPI
      schemas.py               # Pydantic models (API + events)
      kafka_client.py          # Kafka producer
    consumer/                  # Payment consumer service
      payment_consumer.py      # Kafka consumer
      app/
        db.py                  # SQLite for payments
        schemas.py             # Event validation schemas
    asyncapi.yaml              # Event contract specification
    Dockerfile
    README.md

frontends/
  customer-portal/
    src/
      features/
        marketplace/           # Marketplace UI
          MarketplacePage.tsx  # React component
          types.ts             # TypeScript types
      api/
        marketplace.ts         # API client

docker-compose.yml             # Includes Confluent Kafka + services
```

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **Consumer**: aiokafka (Python async Kafka client)
- **Frontend**: React + TypeScript + Vite + Material-UI
- **Event Streaming**: Confluent Kafka (Kafka-compatible)
- **Validation**: Pydantic (OpenAPI + AsyncAPI)
- **Database**: SQLite (payment service only)

## 📖 Key Files

- [`backends/marketplace-py/app/main.py`](app/main.py) - FastAPI app with OpenAPI
- [`backends/marketplace-py/app/schemas.py`](app/schemas.py) - API + event schemas
- [`backends/marketplace-py/consumer/payment_consumer.py`](consumer/payment_consumer.py) - Event consumer
- [`backends/marketplace-py/asyncapi.yaml`](asyncapi.yaml) - Event contract spec
- [`frontends/customer-portal/src/features/marketplace/MarketplacePage.tsx`](../../frontends/customer-portal/src/features/marketplace/MarketplacePage.tsx) - React UI
- [`docker-compose.yml`](../../docker-compose.yml) - Service orchestration

## 🎓 Learning Resources

### OpenAPI
- Auto-generated docs: http://localhost:8006/docs
- OpenAPI spec: http://localhost:8006/openapi.json
- [OpenAPI Specification](https://swagger.io/specification/)

### AsyncAPI
- Event contract: [`asyncapi.yaml`](asyncapi.yaml)
- [AsyncAPI Specification](https://www.asyncapi.com/docs/reference/specification/v3.0.0)
- [AsyncAPI Studio](https://studio.asyncapi.com/) - Visualize contracts

### Kafka Consumer Groups
- [Kafka Consumer Groups Explained](https://kafka.apache.org/documentation/#consumergroups)
- [Confluent Platform Documentation](https://docs.confluent.io/platform/current/overview.html)

### Data Contracts
- [Data Mesh Principles](https://www.datamesh-architecture.com/)
- [Domain-Driven Design (DDD)](https://martinfowler.com/tags/domain%20driven%20design.html)

## 🔍 Observability

### View Kafka Topics

```bash
# Using Kafka CLI tools in the broker container
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --list
docker exec -it kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic orders.created --from-beginning

```

### Check Consumer Groups

```bash
docker exec -it kafka kafka-consumer-groups --bootstrap-server kafka:9092 --list
docker exec -it kafka kafka-consumer-groups --bootstrap-server kafka:9092 --describe --group payment-service-v1
```

### View Payment Database

```bash
# Inside payment-consumer container
docker exec -it payment-consumer sqlite3 /data/payments.db "SELECT * FROM payments;"

# Or locally (if running locally)
sqlite3 backends/marketplace-py/consumer/payments.db "SELECT * FROM payments;"
```

## 🚧 Production Considerations

This is a **minimal demo**. For production:

1. **Schema Registry**: Use Confluent Schema Registry or Confluent Kafka Schema Registry
2. **Monitoring**: Add Prometheus metrics, distributed tracing (OpenTelemetry)
3. **Error Handling**: Dead letter queues, retry policies, circuit breakers
4. **Security**: mTLS for Kafka, API authentication/authorization
5. **Database**: Replace SQLite with PostgreSQL/MySQL
6. **Deployment**: Kubernetes, container orchestration
7. **CI/CD**: Automated testing, contract testing, deployment pipelines

## 📄 License

MIT

---

Built with ❤️ demonstrating modern microservices patterns:
- Contract-first design (OpenAPI + AsyncAPI)
- Event-driven architecture (Kafka)
- Data ownership (bounded contexts)
- Horizontal scaling (consumer groups)
