from datetime import datetime, timezone

import numpy as np
import pandas as pd

from api.mongo_schema import get_realtime_analytics_collection


def _clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def build_analytics_document(
    symbol: str,
    row: pd.Series,
    features: dict,
    prediction: dict | None = None,
    risk: dict | None = None,
    anomaly: dict | None = None,
    metadata: dict | None = None,
):
    """Build one MongoDB realtime_analytics document."""
    timestamp = row["open_time"]
    if isinstance(timestamp, (int, float, np.integer, np.floating)):
        timestamp = datetime.fromtimestamp(float(timestamp) / 1_000_000, tz=timezone.utc)

    return {
        "symbol": symbol,
        "timestamp": timestamp,
        "market": {
            "open": _clean_value(row.get("open")),
            "high": _clean_value(row.get("high")),
            "low": _clean_value(row.get("low")),
            "close": _clean_value(row.get("close")),
            "volume": _clean_value(row.get("volume")),
            "quote_asset_volume": _clean_value(row.get("quote_asset_volume")),
            "num_trades": _clean_value(row.get("num_trades")),
            "taker_buy_base_volume": _clean_value(row.get("taker_buy_base_volume")),
            "taker_buy_quote_volume": _clean_value(row.get("taker_buy_quote_volume")),
        },
        "features": {key: _clean_value(value) for key, value in features.items()},
        "prediction": prediction or {
            "value": None,
            "direction": None,
            "source": "NOT_READY",
            "status": "NOT_READY",
        },
        "risk": risk or {"score": None, "level": None, "source": "NOT_READY"},
        "anomaly": anomaly or {
            "score": None,
            "is_anomaly": None,
            "source": "NOT_READY",
        },
        "metadata": metadata or {
            "pipeline": "RTA_V4",
            "source": "spark_stream",
            "test_record": False,
        },
    }


def upsert_analytics(document: dict):
    collection = get_realtime_analytics_collection()
    return collection.update_one(
        {"symbol": document["symbol"], "timestamp": document["timestamp"]},
        {"$set": document},
        upsert=True,
    )


def write_analytics_batch(documents: list[dict]):
    if not documents:
        return 0

    from pymongo import UpdateOne

    collection = get_realtime_analytics_collection()
    operations = [
        UpdateOne(
            {"symbol": document["symbol"], "timestamp": document["timestamp"]},
            {"$set": document},
            upsert=True,
        )
        for document in documents
    ]
    result = collection.bulk_write(operations, ordered=False)
    return result.upserted_count + result.modified_count
