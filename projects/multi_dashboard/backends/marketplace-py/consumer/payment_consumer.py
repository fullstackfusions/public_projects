"""Payment Consumer Service - Demonstrates event-driven architecture.

This service:
- Consumes events from Kafka (AsyncAPI contract)
- Uses consumer groups for horizontal scaling
- Owns payment data (data contract)
- Validates events with Pydantic schemas
"""
import os
import json
import uuid
import asyncio
from aiokafka import AIOKafkaConsumer

from app.schemas import OrderCreatedEventV1
from app.db import init_db

# Configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "payment-service-v1")  # Consumer group = scaling unit
TOPIC = "orders.created"
DB_PATH = os.getenv("DB_PATH", "./payments.db")


async def consume_orders():
    """Consume order created events and create payments.

    Consumer group 'payment-service-v1' allows:
    - Horizontal scaling (multiple instances share load)
    - Isolation from other services consuming same topic
    - Independent offset management
    """
    # Initialize database (data ownership)
    conn = init_db(DB_PATH)

    # Create Kafka consumer with consumer group
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=GROUP_ID,                  # ✅ Consumer group = scaling unit for THIS service
        auto_offset_reset="earliest",       # Start from beginning if no offset
        enable_auto_commit=True,            # Auto-commit offsets
    )

    print(f"🚀 Starting payment consumer (group: {GROUP_ID})")
    print(f"📡 Listening to topic: {TOPIC}")
    print(f"🔗 Kafka: {KAFKA_BOOTSTRAP}")

    await consumer.start()
    try:
        async for msg in consumer:
            # Decode and validate event against contract
            payload = json.loads(msg.value.decode("utf-8"))
            event = OrderCreatedEventV1.model_validate(payload)  # ✅ Validate against event schema

            # Data contract: payment service OWNS payments, not orders
            payment_id = "pay_" + uuid.uuid4().hex[:10]

            # Store payment in local database
            conn.execute(
                "INSERT OR REPLACE INTO payments(payment_id, order_id, amount_cents, status) VALUES (?, ?, ?, ?)",
                (payment_id, event.order.order_id, event.order.amount_cents, "completed"),
            )
            conn.commit()

            print(f"💳 Created payment {payment_id} for order {event.order.order_id} (${event.order.amount_cents/100:.2f})")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await consumer.stop()
        conn.close()
        print("✅ Payment consumer stopped")


def main():
    """Entry point for payment consumer."""
    asyncio.run(consume_orders())


if __name__ == "__main__":
    main()
