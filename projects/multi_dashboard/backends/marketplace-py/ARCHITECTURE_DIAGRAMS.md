# Marketplace Architecture Diagrams

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐    │
│  │           React Frontend (Port 5173)                  │    │
│  │  ┌─────────────────────────────────────────────┐     │    │
│  │  │  Marketplace UI Component                   │     │    │
│  │  │  - Create orders                            │     │    │
│  │  │  - Display confirmations                    │     │    │
│  │  └─────────────────────────────────────────────┘     │    │
│  └───────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ HTTP Request (OpenAPI)
                       │ POST /orders
                       │ { user_id, amount_cents }
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Marketplace API (Port 8006)                   │
│                     FastAPI + Kafka Producer                    │
│                                                                 │
│  ┌────────────────┐    ┌──────────────────┐                   │
│  │  HTTP Handler  │───▶│  Kafka Producer  │                   │
│  │  POST /orders  │    │  publish event   │                   │
│  └────────────────┘    └──────────────────┘                   │
│                                                                 │
│  Contract: OpenAPI (auto-generated)                            │
│  Data Owned: Orders                                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Kafka Event (AsyncAPI)
                       │ Topic: orders.created
                       │ { order: { order_id, user_id, amount_cents }}
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              Redpanda / Kafka (Port 19092)                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐      │
│  │  Topic: orders.created                              │      │
│  │  - Stores events                                    │      │
│  │  - Routes to consumer groups                        │      │
│  │  - Manages offsets                                  │      │
│  └─────────────────────────────────────────────────────┘      │
│                                                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Consumer Group: payment-service-v1
                       │ (can have multiple instances)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              Payment Consumer (Background Service)              │
│                     Python + Kafka Consumer                     │
│                                                                 │
│  ┌────────────────┐    ┌──────────────────┐                   │
│  │ Kafka Consumer │───▶│  Event Handler   │                   │
│  │ subscribe to   │    │  validate schema │                   │
│  │ orders.created │    │  create payment  │                   │
│  └────────────────┘    └──────────────────┘                   │
│                               │                                 │
│                               ▼                                 │
│                        ┌──────────────┐                        │
│                        │  SQLite DB   │                        │
│                        │ payments.db  │                        │
│                        └──────────────┘                        │
│                                                                 │
│  Contract: AsyncAPI (validated with Pydantic)                  │
│  Data Owned: Payments                                          │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Contract Flow

```
┌─────────────────────┐
│   React Frontend    │
└──────────┬──────────┘
           │
           │ 1. HTTP Request
           │    POST /orders
           │    Content-Type: application/json
           │    Body: { "user_id": "...", "amount_cents": 1999 }
           │
           ▼
┌─────────────────────┐
│  Marketplace API    │
└──────────┬──────────┘
           │
           │ 2. Validate against OpenAPI schema
           │    (Pydantic: CreateOrderRequest)
           │
           │ 3. Create order (in-memory)
           │    order_id = "ord_..."
           │
           │ 4. Publish event
           │    Topic: orders.created
           │    Schema: OrderCreatedEventV1
           │    Payload: { "order": { ... }}
           │
           ▼
┌─────────────────────┐
│    Kafka/Redpanda   │
└──────────┬──────────┘
           │
           │ 5. Store event
           │    Partition by key
           │    Manage offsets
           │
           ▼
┌─────────────────────┐
│  Payment Consumer   │
└──────────┬──────────┘
           │
           │ 6. Consume event
           │    Group: payment-service-v1
           │
           │ 7. Validate against AsyncAPI schema
           │    (Pydantic: OrderCreatedEventV1)
           │
           │ 8. Create payment
           │    payment_id = "pay_..."
           │    INSERT INTO payments(...)
           │
           ▼
      payments.db
```

## 3. Data Ownership

```
┌──────────────────────────────────────────────────────┐
│                 Marketplace API                      │
│                                                      │
│  OWNS: Orders                                        │
│  - Order creation                                    │
│  - Order state management                            │
│  - Order business logic                              │
│                                                      │
│  DOES NOT OWN: Payments                             │
│                                                      │
│  INTEGRATION:                                        │
│  - HTTP API (OpenAPI)                               │
│  - Kafka events (AsyncAPI)                          │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│              Payment Consumer                        │
│                                                      │
│  OWNS: Payments                                      │
│  - Payment creation                                  │
│  - Payment state management                          │
│  - Payment business logic                            │
│  - payments.db database                              │
│                                                      │
│  DOES NOT OWN: Orders                               │
│  (only reads order info from events)                │
│                                                      │
│  INTEGRATION:                                        │
│  - Kafka events (AsyncAPI)                          │
└──────────────────────────────────────────────────────┘

❌ NO SHARED DATABASE
❌ NO SHARED ORM
✅ Integration via API/Events only
```

## 4. Consumer Group Scaling

```
Single Instance:
┌────────────────┐
│     Kafka      │
│ orders.created │
└────────┬───────┘
         │
         │ Consumer Group: payment-service-v1
         ▼
┌────────────────┐
│   Instance 1   │
│ (processes all)│
└────────────────┘


Horizontal Scaling (Multiple Instances):
┌────────────────┐
│     Kafka      │
│ orders.created │
│                │
│ Partition 0    │
│ Partition 1    │
│ Partition 2    │
└───┬────┬───┬───┘
    │    │   │
    │    │   └─────────┐
    │    │             │
    │    └────────┐    │
    │             │    │
    ▼             ▼    ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│Instance 1│ │Instance 2│ │Instance 3│
│Part 0    │ │Part 1    │ │Part 2    │
└──────────┘ └──────────┘ └──────────┘

All in same Consumer Group: payment-service-v1
Kafka distributes partitions across instances
```

## 5. Routing Strategy

```
❌ BAD: Routing via payload flags

Event: {
  "type": "order_created",  ← Routing flag
  "order": { ... }
}

Problems:
- Consumer must parse payload to route
- All consumers see all events
- No topic-level access control


✅ GOOD: Routing via topic names

Topic: orders.created
Payload: {
  "order": { ... }  ← No routing flags
}

Benefits:
- Clear event semantics
- Topic-level subscriptions
- Topic-level access control
- Topic-level retention policies
- Consumers subscribe to specific topics only
```

## 6. Schema Evolution

```
Version 1 (Current):
Topic: orders.created
Schema: OrderCreatedEventV1
{
  "order": {
    "order_id": string,
    "user_id": string,
    "amount_cents": integer
  }
}


Version 2 (Future - Backward Compatible):
Topic: orders.created
Schema: OrderCreatedEventV2
{
  "order": {
    "order_id": string,
    "user_id": string,
    "amount_cents": integer,
    "currency": string,      ← New optional field
    "items": []              ← New optional field
  }
}

Rules:
✅ Add optional fields (with defaults)
✅ Version event models (V1, V2, ...)
❌ Never remove required fields
❌ Never change field types
```

## 7. Request/Response Flow Timing

```
1. User clicks "Create Order"
   |
   | < 1ms
   ▼
2. React sends HTTP request
   |
   | ~ 10-50ms (network)
   ▼
3. API validates request (Pydantic)
   |
   | < 1ms
   ▼
4. API creates order
   |
   | < 1ms
   ▼
5. API publishes event to Kafka
   |
   | ~ 1-5ms (Kafka ack)
   ▼
6. API returns response to React
   |
   | ~ 10-50ms (network)
   ▼
7. User sees confirmation

Total User-Facing Time: ~20-110ms


Meanwhile (Asynchronously):

8. Kafka stores event
   |
   | ~ 1-10ms
   ▼
9. Payment consumer polls Kafka
   |
   | ~ 100-1000ms (poll interval)
   ▼
10. Consumer validates event
    |
    | < 1ms
    ▼
11. Consumer creates payment
    |
    | ~ 1-10ms (SQLite)
    ▼
12. Consumer commits offset

Total Async Processing: ~100-1020ms

Note: User doesn't wait for steps 8-12!
Event-driven = faster perceived response time
```

## 8. Technology Stack Map

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND                         │
│                                                     │
│  React + TypeScript                                │
│  Material-UI                                        │
│  Vite                                              │
│  Axios                                             │
└─────────────────────────────────────────────────────┘
                       │
                       │ HTTP/REST
                       ▼
┌─────────────────────────────────────────────────────┐
│                   BACKEND API                       │
│                                                     │
│  FastAPI (Python 3.11+)                            │
│  Pydantic (validation)                             │
│  Uvicorn (ASGI server)                             │
│  aiokafka (Kafka producer)                         │
└─────────────────────────────────────────────────────┘
                       │
                       │ Kafka Protocol
                       ▼
┌─────────────────────────────────────────────────────┐
│              EVENT STREAMING                        │
│                                                     │
│  Redpanda (Kafka-compatible)                       │
└─────────────────────────────────────────────────────┘
                       │
                       │ Kafka Protocol
                       ▼
┌─────────────────────────────────────────────────────┐
│                   CONSUMER                          │
│                                                     │
│  Python 3.11+                                      │
│  aiokafka (Kafka consumer)                         │
│  Pydantic (validation)                             │
│  SQLite (database)                                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                 ORCHESTRATION                       │
│                                                     │
│  Docker + Docker Compose                           │
│  VS Code Tasks                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                  CONTRACTS                          │
│                                                     │
│  OpenAPI 3.1 (HTTP)                                │
│  AsyncAPI 3.0 (Events)                             │
│  Pydantic (Validation)                             │
└─────────────────────────────────────────────────────┘
```

---

## Legend

```
┌──────┐
│ Box  │  = Service / Component
└──────┘

───▶     = Synchronous call / HTTP request

- - ▶    = Asynchronous message / Event

│
▼        = Data flow direction

┬
├───     = Multiple connections / Fan-out

✅       = Good practice / Implemented

❌       = Bad practice / Anti-pattern
```
