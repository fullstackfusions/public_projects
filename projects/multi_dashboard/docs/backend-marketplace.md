# Marketplace Backend — Event-Driven Architecture with Kafka

**Port:** 8006 | **Stack:** FastAPI + Confluent Kafka

Demonstrates event-driven microservices. When a customer places an order, the marketplace API publishes an event to Kafka. A separate payment service consumes that event and processes the payment — without the two services ever calling each other directly.

**API docs:** http://localhost:8006/docs

---

## What You'll Learn

- What event-driven architecture is and why it's used
- Kafka concepts: topics, producers, consumers, consumer groups
- How to decouple two services using a message queue
- The difference between synchronous (REST) and asynchronous (event) communication
- Contract-first design with OpenAPI (HTTP) and AsyncAPI (events)

---

## The Core Idea

Without events (tightly coupled):
```
Customer → Marketplace API → calls Payment API directly → waits for response
```

With events (loosely coupled):
```
Customer → Marketplace API → publishes "order.created" event → responds immediately
                                          ↓
                              Kafka stores the event
                                          ↓
                              Payment Consumer picks it up → processes payment
```

The marketplace service doesn't know or care about the payment service. You could swap the payment service for a different one, or add more consumers (e.g., an inventory service), without changing the marketplace at all.

---

## How It Works

```
React UI
  → POST /orders (creates an order)
  → marketplace-api publishes to Kafka topic "orders.created"
  → returns 201 immediately (doesn't wait for payment)

payment-consumer (runs separately)
  → subscribes to "orders.created"
  → receives the event
  → creates a payment record in SQLite
  → logs "Created payment for order X"
```

---

## Project Structure

```
backends/marketplace-py/
├── app/
│   ├── main.py       # FastAPI app + Kafka producer
│   └── schemas.py    # Event schemas (Pydantic)
└── consumer/
    └── payment_consumer.py   # Kafka consumer (separate process)
```

---

## Kafka Concepts

**Topic** — a named stream of events, like a channel. Events go in, consumers read them out.

**Producer** — a service that publishes events to a topic.

**Consumer** — a service that reads events from a topic.

**Consumer Group** — a group of consumer instances that share the work. If you run 3 instances of the payment consumer, each order event is processed by only one of them.

**Offset** — where a consumer is in the topic. Kafka remembers which events each consumer group has processed.

---

## Event Schema

Every event published to `orders.created` looks like:

```json
{
  "event_type": "order.created.v1",
  "event_id": "uuid",
  "timestamp": "2026-07-01T10:00:00Z",
  "order": {
    "order_id": "uuid",
    "user_id": "user_123",
    "amount_cents": 4999
  }
}
```

Versioning events (`v1`) is important — it lets you evolve the schema without breaking existing consumers.

---

## Try It

1. Start services: `docker compose up -d kafka zookeeper marketplace-api payment-consumer`
2. Create an order:
```bash
curl -X POST http://localhost:8006/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "amount_cents": 4999}'
```
3. Watch the payment consumer process it:
```bash
docker compose logs payment-consumer | grep "Created payment"
```

---

## Why Not Just Call the Payment API Directly?

Direct calls create coupling problems:
- What if the payment service is down? The order fails.
- What if payment processing is slow? The user waits.
- What if you need to add a third service (e.g., email notifications)?

With Kafka, each service is independent. The marketplace doesn't need to know anything about payment processing — it just drops an event and moves on.
