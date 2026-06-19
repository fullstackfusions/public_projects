# Payment Consumer Service

Event-driven consumer service demonstrating:
- **Consumer Groups**: Horizontal scaling unit (`payment-service-v1`)
- **AsyncAPI Contract**: Validates events with Pydantic schemas
- **Data Ownership**: Owns payment data (separate database)
- **Event-Driven Architecture**: Reacts to order creation events
- **Bounded Context**: Payment domain separated from order domain

## Architecture

```
┌──────────────────┐
│ Marketplace API  │
└────────┬─────────┘
         │ Publishes Event
         │ Topic: orders.created
         ▼
┌──────────────────┐
│  Kafka/Redpanda  │
└────────┬─────────┘
         │ Consumer Group: payment-service-v1
         ▼
┌──────────────────┐
│ Payment Consumer │ ──> payments.db (local)
└──────────────────┘
```

## Consumer Group Benefits

- **Horizontal Scaling**: Run multiple instances to share load
- **Fault Tolerance**: If one instance dies, others continue
- **Isolation**: Independent from other services consuming same topic
- **Offset Management**: Group tracks progress independently

## Data Contract

This service **OWNS**:
- Payment creation
- Payment state management
- Payment business logic
- `payments.db` database

**Does NOT** access order database directly.

## Running Locally

```bash
cd backends/marketplace-py/consumer
python payment_consumer.py
```

## Running with Docker

```bash
docker-compose up payment-consumer
```

## Environment Variables

- `KAFKA_BOOTSTRAP`: Kafka bootstrap servers (default: `localhost:9092`)
- `KAFKA_GROUP_ID`: Consumer group ID (default: `payment-service-v1`)
- `DB_PATH`: SQLite database path (default: `./payments.db`)

## Scaling

To scale horizontally, run multiple instances with the same `KAFKA_GROUP_ID`:

```bash
# Terminal 1
KAFKA_GROUP_ID=payment-service-v1 python payment_consumer.py

# Terminal 2
KAFKA_GROUP_ID=payment-service-v1 python payment_consumer.py

# Kafka will distribute partitions across both instances
```
