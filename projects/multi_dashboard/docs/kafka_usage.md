# Kafka — Event-Driven Architecture Guide

This guide explains how Kafka is used in the marketplace service and covers the core concepts you need to understand event-driven systems.

---

## What Is Kafka?

Kafka is a **distributed event log**. Services publish events to it; other services consume those events. No service calls another service directly.

Think of it like a message board:
- The marketplace API posts "order #123 was created" on the board
- The payment service reads the board and processes order #123
- If the payment service is offline, messages wait — they won't be lost

---

## Core Concepts

**Topic** — A named category of events. Like a folder for a specific type of message.
```
Topic: "orders.created"   ← all order events go here
Topic: "payments.completed" ← all payment events go here
```

**Producer** — A service that writes events to a topic.

**Consumer** — A service that reads events from a topic.

**Consumer Group** — Multiple instances of the same consumer sharing the work. Kafka ensures each event is processed by only one instance in the group.

**Offset** — A pointer to where in the topic a consumer has read up to. Kafka tracks this per consumer group.

---

## How It Works in This Project

```
marketplace-api (producer)           payment-consumer (consumer)
       │                                      │
       │  POST /orders                        │  reads from topic
       │  → creates order                     │  "orders.created"
       │  → publishes event ──────────────►  │  → creates payment
       │  → returns 201 ✓                    │  → logs result
       │                                      │
       └──────── Kafka topic "orders.created" ┘
                 stores events durably
```

---

## The Event Schema

Every event published to `orders.created` follows this schema:

```python
class OrderCreatedEventV1(BaseModel):
    event_type: str = "order.created.v1"
    event_id: str                    # unique ID for deduplication
    timestamp: datetime
    order: OrderData
```

**Why version events?** (`v1`) When you need to change an event's structure, you create `v2` instead of modifying `v1`. Old consumers keep working; new consumers can use `v2`.

---

## Producer Code (marketplace-api)

```python
# On startup
producer = AIOKafkaProducer(bootstrap_servers="kafka:9092")
await producer.start()

# When an order is created
event = OrderCreatedEventV1(order=order_data)
await producer.send_and_wait(
    "orders.created",                    # topic name
    value=json.dumps(event.dict()).encode()
)
```

`send_and_wait` blocks until Kafka confirms the message was received. The API only returns 201 to the client after Kafka confirms.

---

## Consumer Code (payment-consumer)

```python
consumer = AIOKafkaConsumer(
    "orders.created",                    # topic to read from
    bootstrap_servers="kafka:9092",
    group_id="payment-service-v1",       # consumer group
)
await consumer.start()

async for message in consumer:
    event = json.loads(message.value)
    # process the order event
    await create_payment(event["order"])
```

The `group_id` is the consumer group. If you run two instances of this consumer, Kafka automatically splits events between them.

---

## Scaling with Consumer Groups

```
Topic "orders.created" has 3 partitions

Consumer group "payment-service-v1" with 3 instances:
  Instance A ← reads partition 0
  Instance B ← reads partition 1
  Instance C ← reads partition 2
```

To handle more orders, add more consumer instances. Kafka redistributes partitions automatically.

---

## Docker Setup

```yaml
# In docker-compose.yml
kafka:
  image: confluentinc/cp-kafka:7.6.1
  ports:
    - "19100:19092"        # host:container
  environment:
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    KAFKA_ADVERTISED_LISTENERS: |
      PLAINTEXT://kafka:9092,         # internal (container-to-container)
      EXTERNAL://localhost:19100      # external (host machine)
```

- **Internal address** `kafka:9092` — used by marketplace-api and payment-consumer when running in Docker
- **External address** `localhost:19100` — used when running a service locally outside Docker
