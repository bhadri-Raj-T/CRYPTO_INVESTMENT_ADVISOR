# producer/kafka_producer.py
import json
import logging
from kafka import KafkaProducer

from producer.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC

logger = logging.getLogger("kafka_producer")


def build_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",          # wait for broker to confirm write
        linger_ms=10,        # tiny batching window, keeps latency low but batches bursts
        retries=5,
    )


def send_tick(producer: KafkaProducer, message: dict):
    """
    Keys the message by symbol so Kafka's default partitioner sends
    all of one coin's ticks to the same partition consistently.
    """
    key = message.get("symbol")
    producer.send(KAFKA_TOPIC, key=key, value=message)