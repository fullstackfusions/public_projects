# Marketplace API

**Port:** 8006 | FastAPI + Confluent Kafka

An event-driven service that publishes order events to Kafka. A separate `payment-consumer` service picks up those events and processes payments — without the two services ever calling each other directly.

**API docs:** http://localhost:8006/docs

---

## How It Works

```
POST /orders  →  marketplace-api publishes "orders.created" event to Kafka
                                    ↓
                       payment-consumer reads the event
                       → creates a payment record
```

---

## Run It

```bash
# Start Kafka + both services
docker compose up kafka zookeeper marketplace-api payment-consumer

# Create an order
curl -X POST http://localhost:8006/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "amount_cents": 4999}'

# Verify the payment consumer processed it
docker compose logs payment-consumer | grep "Created payment"
```

---

## Project Layout

```
marketplace-py/
├── app/
│   ├── main.py        # FastAPI + Kafka producer
│   └── schemas.py     # Event schemas
└── consumer/
    └── payment_consumer.py  # Kafka consumer (separate process)
```

---

## See Also

- [docs/backend-marketplace.md](../../docs/backend-marketplace.md) — full guide with Kafka concepts explained
- [docs/kafka_usage.md](../../docs/kafka_usage.md) — Kafka deep-dive
