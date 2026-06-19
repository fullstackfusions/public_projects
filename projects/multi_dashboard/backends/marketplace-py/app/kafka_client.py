"""Kafka producer client for publishing events."""
import json
from aiokafka import AIOKafkaProducer


def json_dumps(obj) -> bytes:
    """Serialize object to JSON bytes."""
    return json.dumps(obj, default=str).encode("utf-8")


async def make_producer(bootstrap: str) -> AIOKafkaProducer:
    """Create and start a Kafka producer.

    Args:
        bootstrap: Kafka bootstrap servers (e.g., "localhost:9092")

    Returns:
        Started AIOKafkaProducer instance
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=json_dumps
    )
    await producer.start()
    return producer
