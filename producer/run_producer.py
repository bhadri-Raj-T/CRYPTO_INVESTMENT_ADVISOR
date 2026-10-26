# Auto-generated scaffold for run_producer.py
# producer/run_producer.py
import asyncio
import logging

from producer.binance_ws_client import listen
from producer.kafka_producer import build_producer, send_tick

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_producer")


def main():
    producer = build_producer()

    def handle_message(message: dict):
        send_tick(producer, message)
        logger.info(f"Produced: {message['stream_type']} | {message['symbol']} | event_time={message['event_time']}")

    try:
        asyncio.run(listen(handle_message))
    except KeyboardInterrupt:
        logger.info("Shutting down producer...")
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()