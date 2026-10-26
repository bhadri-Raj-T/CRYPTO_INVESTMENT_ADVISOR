"""Create the lightweight RTA V4 runtime assets from the completed training project.

This copies only:
- 4 small GRU V4 checkpoints
- 4 StandardScaler files
- optional final result JSON files
- the last 240 raw 1-minute candles per asset for fast Spark bootstrap
- the comparison report when present

It does not copy master history, processed training arrays, predictions or training logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT")
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_required(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default=r"E:\crypto-rt-analytics",
        help="Completed training project root",
    )
    parser.add_argument(
        "--runtime",
        default=str(Path(__file__).resolve().parents[1]),
        help="RTA runtime project root",
    )
    parser.add_argument("--bootstrap-rows", type=int, default=240)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    runtime = Path(args.runtime).resolve()
    model_root = runtime / "runtime_assets" / "models"
    bootstrap_root = runtime / "runtime_assets" / "bootstrap"
    report_root = runtime / "runtime_assets" / "reports"

    print("=" * 78)
    print("RTA V4 LIGHTWEIGHT RUNTIME ASSET PREPARATION")
    print("=" * 78)
    print("Training project :", source)
    print("Runtime project  :", runtime)
    print("Bootstrap rows   :", args.bootstrap_rows)

    manifest = {
        "source_project": str(source),
        "symbols": {},
        "bootstrap_rows": args.bootstrap_rows,
    }

    for symbol in SYMBOLS:
        print(f"\n[{symbol}]")
        src_model = source / "training" / "models" / "gru_v4" / symbol / "best_model_v4.pt"
        src_scaler = source / "training" / "data" / "processed" / "gru_v4" / symbol / "scaler.joblib"
        src_results = source / "training" / "models" / "gru_v4" / symbol / "results_v4.json"
        src_master = source / "training" / "data" / "master" / f"{symbol}_1m.parquet"

        dst_dir = model_root / symbol
        dst_model = dst_dir / "best_model_v4.pt"
        dst_scaler = dst_dir / "scaler.joblib"
        dst_results = dst_dir / "results_v4.json"
        dst_bootstrap = bootstrap_root / f"{symbol}_1m.parquet"

        copy_required(src_model, dst_model)
        copy_required(src_scaler, dst_scaler)
        if src_results.exists():
            copy_required(src_results, dst_results)

        if not src_master.exists():
            raise FileNotFoundError(src_master)
        frame = pd.read_parquet(src_master, columns=REQUIRED_COLUMNS)
        frame = (
            frame.sort_values("open_time")
            .drop_duplicates(subset=["open_time"], keep="last")
            .tail(args.bootstrap_rows)
            .reset_index(drop=True)
        )
        if len(frame) < 160:
            raise RuntimeError(f"{symbol}: only {len(frame)} bootstrap rows available; need at least 160")
        bootstrap_root.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(dst_bootstrap, index=False)

        manifest["symbols"][symbol] = {
            "checkpoint": str(dst_model.relative_to(runtime)),
            "checkpoint_sha256": sha256(dst_model),
            "scaler": str(dst_scaler.relative_to(runtime)),
            "scaler_sha256": sha256(dst_scaler),
            "bootstrap": str(dst_bootstrap.relative_to(runtime)),
            "bootstrap_rows": len(frame),
        }
        print("  checkpoint :", dst_model)
        print("  scaler     :", dst_scaler)
        print("  bootstrap  :", dst_bootstrap, f"({len(frame)} rows)")

    source_comparison = source / "training" / "models" / "gru_v4" / "comparison_report.json"
    if source_comparison.exists():
        report_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_comparison, report_root / "comparison_report.json")
        print("\nComparison report copied from completed training run.")

    runtime_assets = runtime / "runtime_assets"
    runtime_assets.mkdir(parents=True, exist_ok=True)
    (runtime_assets / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("RUNTIME ASSETS READY")
    print("=" * 78)
    print("The runtime project no longer needs the full training/data/master or processed arrays.")


if __name__ == "__main__":
    main()
