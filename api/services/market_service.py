from __future__ import annotations

from functools import lru_cache
from math import exp, isfinite
from pathlib import Path
from typing import Any

import pandas as pd

from api.database import realtime_analytics_collection


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT")
RUNTIME_ROOT = Path(__file__).resolve().parents[2]
HISTORY_ROOT = RUNTIME_ROOT / "runtime_assets" / "history"

PERIOD_DAYS = {
    "1d": 1,
    "7d": 7,
    "30d": 30,
}

AUTO_INTERVAL = {
    "1d": "5min",
    "7d": "15min",
    "30d": "1h",
}

INTERVAL_ALIASES = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

MARKET_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_asset_volume",
    "num_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]


def _latest_for_symbol(symbol: str):
    return realtime_analytics_collection.find_one(
        {"symbol": symbol},
        sort=[("timestamp", -1)],
    )


def _serialize_document(document: dict | None) -> dict | None:
    if not document:
        return document
    result = dict(document)
    if "_id" in result:
        result["_id"] = str(result["_id"])
    return result



def _utc_timestamp(value):
    """Normalize MongoDB, pandas and Python timestamps to UTC-aware datetimes."""
    if value is None:
        return None
    try:
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            return None
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return ts
    except Exception:
        return None


def get_latest_market_analytics():
    data = []
    for symbol in SYMBOLS:
        document = _latest_for_symbol(symbol)
        if document:
            data.append(_serialize_document(document))
    return {"count": len(data), "data": data}


def get_market_symbol(symbol: str):
    return _serialize_document(_latest_for_symbol(symbol))


def _timestamp_series(frame: pd.DataFrame) -> pd.Series:
    if "open_time" in frame.columns:
        raw = pd.to_numeric(frame["open_time"], errors="coerce")
    elif "timestamp" in frame.columns:
        raw = pd.to_numeric(frame["timestamp"], errors="coerce")
    else:
        return pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns, UTC]")

    valid = raw.dropna()
    if valid.empty:
        return pd.to_datetime(raw, utc=True, errors="coerce")

    median = float(valid.median())
    if median > 1e14:
        return pd.to_datetime(raw, unit="us", utc=True, errors="coerce")
    if median > 1e11:
        return pd.to_datetime(raw, unit="ms", utc=True, errors="coerce")
    return pd.to_datetime(raw, unit="s", utc=True, errors="coerce")


@lru_cache(maxsize=8)
def _load_history_file(symbol: str) -> pd.DataFrame:
    path = HISTORY_ROOT / f"{symbol}_1m.parquet"
    if not path.exists():
        return pd.DataFrame()

    frame = pd.read_parquet(path)
    if frame.empty:
        return frame

    frame = frame.copy()
    frame["timestamp_dt"] = _timestamp_series(frame)
    frame = frame.dropna(subset=["timestamp_dt"]).sort_values("timestamp_dt")
    frame = frame.drop_duplicates(subset=["timestamp_dt"], keep="last")

    for column in MARKET_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame.reset_index(drop=True)


def _period_slice(frame: pd.DataFrame, period: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    days = PERIOD_DAYS.get(period, 30)
    reference_end = frame["timestamp_dt"].max()
    reference_start = reference_end - pd.Timedelta(days=days)
    return frame[frame["timestamp_dt"] >= reference_start].copy()


def _resample_history(frame: pd.DataFrame, interval: str) -> pd.DataFrame:
    if frame.empty:
        return frame

    rule = INTERVAL_ALIASES.get(interval, interval)
    if rule in ("1min", "1m"):
        return frame.copy()

    indexed = frame.set_index("timestamp_dt").sort_index()
    aggregations: dict[str, Any] = {}
    if "open" in indexed.columns:
        aggregations["open"] = "first"
    if "high" in indexed.columns:
        aggregations["high"] = "max"
    if "low" in indexed.columns:
        aggregations["low"] = "min"
    if "close" in indexed.columns:
        aggregations["close"] = "last"
    for column in (
        "volume",
        "quote_asset_volume",
        "num_trades",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ):
        if column in indexed.columns:
            aggregations[column] = "sum"

    if not aggregations:
        return frame.copy()

    sampled = indexed.resample(rule).agg(aggregations)
    if "close" in sampled.columns:
        sampled = sampled.dropna(subset=["close"])
    else:
        sampled = sampled.dropna(how="all")
    return sampled.reset_index()


def _history_records(symbol: str, frame: pd.DataFrame) -> list[dict]:
    records: list[dict] = []
    for row in frame.to_dict(orient="records"):
        timestamp = row.pop("timestamp_dt")
        row.pop("open_time", None)
        market = {
            key: (None if pd.isna(row.get(key)) else row.get(key))
            for key in MARKET_COLUMNS
            if key in row
        }
        normalized_ts = _utc_timestamp(timestamp)
        records.append(
            {
                "symbol": symbol,
                "timestamp": normalized_ts.to_pydatetime() if normalized_ts is not None else None,
                "market": market,
                "prediction": None,
                "source_type": "historical",
            }
        )
    return records


def _prediction_forecast(document: dict) -> dict:
    prediction = document.get("prediction") or {}
    market = document.get("market") or {}
    close = market.get("close")
    value = prediction.get("predicted_log_return", prediction.get("value"))
    timestamp = document.get("timestamp")

    try:
        close_f = float(close)
        value_f = float(value)
    except (TypeError, ValueError):
        return {}

    if not (isfinite(close_f) and isfinite(value_f)):
        return {}

    try:
        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        forecast_ts = ts + pd.Timedelta(minutes=15)
    except Exception:
        return {}

    return {
        "forecast_price": close_f * exp(value_f),
        "forecast_timestamp": forecast_ts.to_pydatetime(),
    }


def _live_records(symbol: str) -> list[dict]:
    documents = list(
        realtime_analytics_collection.find({"symbol": symbol}).sort("timestamp", 1)
    )
    results: list[dict] = []
    for document in documents:
        item = _serialize_document(document) or {}
        normalized_ts = _utc_timestamp(item.get("timestamp"))
        if normalized_ts is not None:
            item["timestamp"] = normalized_ts.to_pydatetime()
        item["source_type"] = "live"
        item.update(_prediction_forecast(item))
        results.append(item)
    return results


def _close_from_record(record: dict) -> float | None:
    market = record.get("market") or {}
    value = market.get("close", record.get("close"))
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _period_stats(records: list[dict], period: str) -> dict:
    closes = [x for x in (_close_from_record(record) for record in records) if x is not None]
    if not closes:
        return {
            "period": period,
            "change_percent": None,
            "high": None,
            "low": None,
            "first_close": None,
            "last_close": None,
        }

    first_close = closes[0]
    last_close = closes[-1]
    change = ((last_close / first_close) - 1.0) * 100.0 if first_close else None
    return {
        "period": period,
        "change_percent": change,
        "high": max(closes),
        "low": min(closes),
        "first_close": first_close,
        "last_close": last_close,
    }


def get_market_history(
    symbol: str,
    limit: int = 1000,
    period: str = "30d",
    interval: str = "auto",
):
    symbol = symbol.upper()
    period = period.lower() if period else "30d"
    if period not in PERIOD_DAYS:
        period = "30d"

    if interval == "auto":
        interval = AUTO_INTERVAL[period]
    interval = interval.lower()
    if interval not in INTERVAL_ALIASES:
        interval = AUTO_INTERVAL[period]

    historical = _period_slice(_load_history_file(symbol), period)
    historical = _resample_history(historical, interval)
    historical_records = _history_records(symbol, historical)
    live_records = _live_records(symbol)

    # Do not create an artificial continuous price line across a large gap.
    # The UI renders historical and live data as separate traces.
    combined = historical_records + live_records

    def _sort_key(item):
        ts = _utc_timestamp(item.get("timestamp"))
        # Invalid/missing timestamps sort last instead of crashing the endpoint.
        return ts.value if ts is not None else 2**63 - 1

    combined.sort(key=_sort_key)

    safe_limit = max(1, min(int(limit), 5000))
    if len(combined) > safe_limit:
        # Preserve at least the newest live observations and sample the historical side.
        live_count = len(live_records)
        live_keep = min(live_count, safe_limit)
        historical_budget = max(0, safe_limit - live_keep)
        hist_keep = historical_records[-historical_budget:] if historical_budget else []
        combined = hist_keep + live_records[-live_keep:]

    # Period statistics come from one coherent time window. Historical reference
    # is preferred; live-only stats are used only when no reference file exists.
    stats_source = historical_records if historical_records else live_records
    stats = _period_stats(stats_source, period)
    history_file = HISTORY_ROOT / f"{symbol}_1m.parquet"
    reference_start = historical_records[0].get("timestamp") if historical_records else None
    reference_end = historical_records[-1].get("timestamp") if historical_records else None

    return {
        "symbol": symbol,
        "period": period,
        "interval": interval,
        "count": len(combined),
        "historical_count": len([x for x in combined if x.get("source_type") == "historical"]),
        "live_count": len([x for x in combined if x.get("source_type") == "live"]),
        "historical_available": history_file.exists(),
        "reference_start": reference_start,
        "reference_end": reference_end,
        "stats": stats,
        "data": combined,
    }


def _finite_float(value):
    try:
        number = float(value)
        return number if isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _latest_outlook_payload(symbol: str, horizon_minutes: int = 60) -> dict:
    """Build a review-friendly forecast horizon without pretending V4 is multi-horizon.

    The trained GRU V4 output is used only at +15 minutes. Points beyond +15m are
    explicitly marked SCENARIO_EXTENSION and are a decaying continuation of the
    latest predicted log return. They are visualization aids, not extra trained
    model outputs.
    """
    symbol = symbol.upper()
    document = _latest_for_symbol(symbol)
    if not document:
        return {
            "symbol": symbol,
            "status": "NO_LIVE_RECORD",
            "model_horizon_minutes": 15,
            "requested_horizon_minutes": int(horizon_minutes),
            "points": [],
        }

    item = _serialize_document(document) or {}
    market = item.get("market") or {}
    prediction = item.get("prediction") or {}
    timestamp = _utc_timestamp(item.get("timestamp"))
    close = _finite_float(market.get("close"))
    raw_return = _finite_float(
        prediction.get("predicted_log_return", prediction.get("value"))
    )

    base = {
        "symbol": symbol,
        "status": prediction.get("status") or ("OK" if raw_return is not None else "NOT_READY"),
        "model": "GRU_V4",
        "model_horizon_minutes": 15,
        "requested_horizon_minutes": int(horizon_minutes),
        "current_price": close,
        "source_timestamp": timestamp.to_pydatetime() if timestamp is not None else None,
        "direction": prediction.get("direction"),
        "probability_up": _finite_float(prediction.get("probability_up")),
        "probability_down": _finite_float(prediction.get("probability_down")),
        "predicted_log_return": raw_return,
        "points": [],
        "note": (
            "Only +15m is a direct GRU V4 output. Later points are labelled "
            "SCENARIO_EXTENSION and are not separately trained predictions."
        ),
    }

    if close is None or raw_return is None or timestamp is None:
        return base

    requested = max(15, min(int(horizon_minutes), 240))
    steps = max(1, requested // 15)
    points = [
        {
            "horizon_minutes": 0,
            "timestamp": timestamp.to_pydatetime(),
            "price": close,
            "move_percent": 0.0,
            "kind": "CURRENT",
            "label": "Now",
        }
    ]

    cumulative_return = 0.0
    decay = 0.65
    for step in range(1, steps + 1):
        if step == 1:
            incremental_return = raw_return
            kind = "DIRECT_MODEL"
            label = "+15m model"
        else:
            incremental_return = raw_return * (decay ** (step - 1))
            kind = "SCENARIO_EXTENSION"
            label = f"+{step * 15}m scenario"
        cumulative_return += incremental_return
        forecast_price = close * exp(cumulative_return)
        move_percent = ((forecast_price / close) - 1.0) * 100.0 if close else None
        points.append(
            {
                "horizon_minutes": step * 15,
                "timestamp": (timestamp + pd.Timedelta(minutes=step * 15)).to_pydatetime(),
                "price": forecast_price,
                "move_percent": move_percent,
                "kind": kind,
                "label": label,
            }
        )

    base["requested_horizon_minutes"] = requested
    base["points"] = points
    base["direct_forecast"] = points[1] if len(points) > 1 else None
    return base


def get_market_outlook(symbol: str, horizon_minutes: int = 60):
    return _latest_outlook_payload(symbol, horizon_minutes=horizon_minutes)


def get_market_overview(period: str = "1d"):
    """Compact four-asset snapshot for the review dashboard."""
    period = period.lower() if period else "1d"
    if period not in PERIOD_DAYS:
        period = "1d"

    now = pd.Timestamp.now(tz="UTC")
    data = []
    for symbol in SYMBOLS:
        document = _latest_for_symbol(symbol)
        if not document:
            data.append({"symbol": symbol, "status": "NO_LIVE_RECORD"})
            continue

        item = _serialize_document(document) or {}
        market = item.get("market") or {}
        prediction = item.get("prediction") or {}
        risk = item.get("risk") or {}
        anomaly = item.get("anomaly") or {}
        timestamp = _utc_timestamp(item.get("timestamp"))
        close = _finite_float(market.get("close"))

        # Historical reference statistics are intentionally labelled as reference
        # context because the parquet file is a completed-dataset asset.
        historical = _period_slice(_load_history_file(symbol), period)
        reference_records = _history_records(symbol, historical)
        stats = _period_stats(reference_records, period)

        outlook = _latest_outlook_payload(symbol, horizon_minutes=15)
        direct = outlook.get("direct_forecast") or {}
        age_seconds = None
        if timestamp is not None:
            age_seconds = max(0.0, float((now - timestamp).total_seconds()))

        data.append(
            {
                "symbol": symbol,
                "status": "LIVE",
                "timestamp": timestamp.to_pydatetime() if timestamp is not None else None,
                "age_seconds": age_seconds,
                "price": close,
                "reference_change_percent": stats.get("change_percent"),
                "reference_high": stats.get("high"),
                "reference_low": stats.get("low"),
                "direction": prediction.get("direction"),
                "probability_up": _finite_float(prediction.get("probability_up")),
                "forecast_price_15m": direct.get("price"),
                "forecast_move_percent_15m": direct.get("move_percent"),
                "risk_level": risk.get("level"),
                "risk_score": _finite_float(risk.get("score")),
                "is_anomaly": bool(anomaly.get("is_anomaly", False)),
                "anomaly_score": _finite_float(anomaly.get("score")),
            }
        )

    return {
        "period": period,
        "generated_at": now.to_pydatetime(),
        "count": len(data),
        "data": data,
        "reference_note": (
            "Reference change/high/low come from the prepared historical parquet asset; "
            "live price, forecast, risk and anomaly fields come from the current stream."
        ),
    }

