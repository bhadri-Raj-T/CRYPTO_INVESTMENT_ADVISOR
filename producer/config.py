# Auto-generated scaffold for config.py
# producer/config.py

# Symbols to track (lowercase, as Binance stream names require lowercase)
SYMBOLS = ["btcusdt", "ethusdt", "bnbusdt", "solusdt"]

# Binance combined stream endpoint
BINANCE_WS_BASE_URL = "wss://stream.binance.com:443/stream"

def build_stream_url() -> str:
    """
    Builds the combined stream URL for trade + 1m kline for every symbol.
    Example single stream name: btcusdt@trade, btcusdt@kline_1m
    """
    streams = []
    for sym in SYMBOLS:
        streams.append(f"{sym}@trade")
        streams.append(f"{sym}@kline_1m")
    stream_param = "/".join(streams)
    return f"{BINANCE_WS_BASE_URL}?streams={stream_param}"

import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BROKER",
    "localhost:9092",
)
KAFKA_TOPIC = "crypto-ticks"

# Reconnect behavior for the WS client
WS_RECONNECT_DELAY_SECONDS = 5