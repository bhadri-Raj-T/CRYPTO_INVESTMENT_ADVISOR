# producer/binance_ws_client.py

import asyncio
import json
import logging
import websockets

from producer.config import build_stream_url, WS_RECONNECT_DELAY_SECONDS


logger = logging.getLogger("binance_ws_client")
logging.basicConfig(level=logging.INFO)


def normalize_message(raw: dict) -> dict | None:
    """
    Normalize Binance combined-stream messages into one common schema.

    Supports:
        - trade
        - kline

    The normalized kline schema preserves all fields required by
    the training feature pipeline, including taker-buy volumes.
    """

    stream_name = raw.get("stream", "")
    data = raw.get("data", {})
    event_type = data.get("e")

    # ========================================================
    # TRADE
    # ========================================================

    if event_type == "trade":

        return {
            "stream_type": "trade",
            "symbol": data.get("s"),
            "event_time": data.get("E"),

            "trade_id": data.get("t"),
            "price": float(data.get("p")),
            "quantity": float(data.get("q")),
            "buyer_order_id": data.get("b"),
            "seller_order_id": data.get("a"),
            "trade_time": data.get("T"),
            "is_buyer_maker": data.get("m"),

            # Kline fields
            "kline_start_time": None,
            "kline_close_time": None,
            "kline_interval": None,
            "kline_open": None,
            "kline_high": None,
            "kline_low": None,
            "kline_close": None,
            "kline_volume": None,
            "kline_num_trades": None,
            "kline_is_closed": None,
            "kline_quote_volume": None,

            # Taker-buy fields
            "taker_buy_base_volume": None,
            "taker_buy_quote_volume": None,
        }

    # ========================================================
    # KLINE
    # ========================================================

    elif event_type == "kline":

        k = data.get("k", {})

        return {
            "stream_type": "kline",
            "symbol": data.get("s"),
            "event_time": data.get("E"),

            # Trade fields
            "trade_id": None,
            "price": None,
            "quantity": None,
            "buyer_order_id": None,
            "seller_order_id": None,
            "trade_time": None,
            "is_buyer_maker": None,

            # Kline fields
            "kline_start_time": k.get("t"),
            "kline_close_time": k.get("T"),
            "kline_interval": k.get("i"),
            "kline_open": float(k.get("o")),
            "kline_high": float(k.get("h")),
            "kline_low": float(k.get("l")),
            "kline_close": float(k.get("c")),
            "kline_volume": float(k.get("v")),
            "kline_num_trades": k.get("n"),
            "kline_is_closed": k.get("x"),
            "kline_quote_volume": float(k.get("q")),

            # ------------------------------------------------
            # IMPORTANT:
            # Binance kline:
            #
            # V = taker buy base asset volume
            # Q = taker buy quote asset volume
            # ------------------------------------------------
            "taker_buy_base_volume": float(k.get("V")),
            "taker_buy_quote_volume": float(k.get("Q")),
        }

    # ========================================================
    # UNKNOWN
    # ========================================================

    else:

        logger.warning(
            f"Unrecognized event type on stream "
            f"{stream_name}: {event_type}"
        )

        return None


async def listen(on_message):

    url = build_stream_url()

    while True:

        try:

            logger.info(
                f"Connecting to {url}"
            )

            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=20,
                open_timeout=15,
            ) as ws:

                logger.info(
                    "Connected. Listening for ticks..."
                )

                async for raw_msg in ws:

                    parsed = json.loads(raw_msg)

                    normalized = normalize_message(
                        parsed
                    )

                    if normalized:
                        on_message(normalized)

        except Exception as e:

            logger.exception(
                f"WebSocket connection failed: "
                f"{type(e).__name__}: {e}"
            )

            await asyncio.sleep(
                WS_RECONNECT_DELAY_SECONDS
            )