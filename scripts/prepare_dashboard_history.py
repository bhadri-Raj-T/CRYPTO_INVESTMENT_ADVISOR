"""Prepare a current historical reference for the RTA dashboard.

Default behaviour (`--mode auto`):
1. Download the latest 30 days of 1-minute Binance klines so the historical
   chart connects naturally to the current live stream.
2. If Binance REST is unavailable, fall back to the last 30 days available in
   the completed training master Parquet files.

The result is stored under runtime_assets/history and is read directly by
FastAPI. Old history is not inserted into MongoDB.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT")
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
REQUIRED_COLUMNS = [
    "open_time",
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


def fetch_binance_history(symbol: str, days: int) -> pd.DataFrame:
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = end_ms - int(days * 24 * 60 * 60 * 1000)
    cursor = start_ms
    rows: list[list] = []

    session = requests.Session()
    while cursor < end_ms:
        response = session.get(
            BINANCE_KLINES,
            params={
                "symbol": symbol,
                "interval": "1m",
                "startTime": cursor,
                "endTime": end_ms,
                "limit": 1000,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload:
            break
        rows.extend(payload)
        next_cursor = int(payload[-1][0]) + 60_000
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        # Be conservative with public REST rate limits.
        time.sleep(0.04)

    if not rows:
        raise RuntimeError(f"{symbol}: Binance returned no historical klines")

    frame = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "num_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )
    frame = frame[REQUIRED_COLUMNS].copy()
    numeric = [c for c in REQUIRED_COLUMNS if c != "open_time"]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["open_time"] = pd.to_numeric(frame["open_time"], errors="coerce").astype("Int64")
    frame = frame.dropna(subset=["open_time", "close"])
    frame["open_time"] = frame["open_time"].astype("int64")
    return (
        frame.sort_values("open_time")
        .drop_duplicates(subset=["open_time"], keep="last")
        .reset_index(drop=True)
    )


def load_master_history(source: Path, symbol: str, days: int) -> pd.DataFrame:
    src = source / "training" / "data" / "master" / f"{symbol}_1m.parquet"
    if not src.exists():
        raise FileNotFoundError(src)
    rows_requested = max(1, days) * 1440
    frame = pd.read_parquet(src, columns=REQUIRED_COLUMNS)
    return (
        frame.sort_values("open_time")
        .drop_duplicates(subset=["open_time"], keep="last")
        .tail(rows_requested)
        .reset_index(drop=True)
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=r"E:\crypto-rt-analytics")
    parser.add_argument(
        "--runtime",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--mode",
        choices=("auto", "binance", "master"),
        default="auto",
        help="auto uses current Binance history and falls back to training master data",
    )
    args = parser.parse_args()

    source = Path(args.source).resolve()
    runtime = Path(args.runtime).resolve()
    history_root = runtime / "runtime_assets" / "history"
    history_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "days": int(args.days),
        "requested_mode": args.mode,
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbols": {},
    }

    print("=" * 78)
    print("RTA CURRENT DASHBOARD HISTORY PREPARATION")
    print("=" * 78)
    print("Runtime project :", runtime)
    print("History window  :", args.days, "days")
    print("Mode            :", args.mode)

    for symbol in SYMBOLS:
        dst = history_root / f"{symbol}_1m.parquet"
        used_source = None
        error_message = None

        if args.mode in ("auto", "binance"):
            try:
                print(f"\n[{symbol}] downloading current Binance 1m history...")
                frame = fetch_binance_history(symbol, args.days)
                used_source = "binance_rest"
            except Exception as exc:
                error_message = str(exc)
                if args.mode == "binance":
                    raise
                print(f"  Binance download unavailable: {exc}")
                print("  Falling back to completed training master data...")
                frame = load_master_history(source, symbol, args.days)
                used_source = "training_master_fallback"
        else:
            print(f"\n[{symbol}] reading completed training master data...")
            frame = load_master_history(source, symbol, args.days)
            used_source = "training_master"

        if frame.empty:
            raise RuntimeError(f"{symbol}: no historical rows available")

        frame.to_parquet(dst, index=False)
        manifest["symbols"][symbol] = {
            "rows": int(len(frame)),
            "file": str(dst.relative_to(runtime)),
            "source": used_source,
            "fallback_reason": error_message,
            "first_open_time": int(frame["open_time"].iloc[0]),
            "last_open_time": int(frame["open_time"].iloc[-1]),
        }
        print(f"  source : {used_source}")
        print(f"  rows   : {len(frame):,}")
        print(f"  saved  : {dst}")

    (history_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 78)
    print("DASHBOARD HISTORY READY")
    print("=" * 78)
    print("FastAPI will merge this reference with MongoDB live records at request time.")


if __name__ == "__main__":
    main()
