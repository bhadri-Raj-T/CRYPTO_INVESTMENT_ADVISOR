from __future__ import annotations

import json
from pathlib import Path

from api.database import realtime_analytics_collection

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "runtime_assets" / "reports" / "comparison_report.json"
MODEL_ROOT = PROJECT_ROOT / "runtime_assets" / "models"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT")


def _read_report() -> dict:
    if not REPORT_PATH.exists():
        return {"gru_v4": {}, "xgboost": {}, "chronos2": {}, "notes": []}
    try:
        payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get_model_comparison() -> dict:
    payload = _read_report()
    payload["report_file"] = str(REPORT_PATH)
    return payload


def get_model_summary() -> dict:
    report = _read_report()
    gru = report.get("gru_v4", {}) if isinstance(report, dict) else {}
    assets = []
    for symbol in SYMBOLS:
        model_dir = MODEL_ROOT / symbol
        latest = realtime_analytics_collection.find_one(
            {"symbol": symbol},
            sort=[("timestamp", -1)],
            projection={"prediction": 1, "timestamp": 1, "_id": 0},
        )
        assets.append(
            {
                "symbol": symbol,
                "model_version": "GRU_V4",
                "source": "GRU_V4_ASSET_SPECIFIC_EXPERIMENTAL",
                "sequence_length": 60,
                "feature_count": 50,
                "forecast_horizon_minutes": 15,
                "checkpoint_ready": (model_dir / "best_model_v4.pt").exists(),
                "scaler_ready": (model_dir / "scaler.joblib").exists(),
                "test_metrics": gru.get(symbol, {}),
                "latest_prediction": (latest or {}).get("prediction"),
                "latest_prediction_timestamp": (latest or {}).get("timestamp"),
            }
        )
    return {
        "model_family": "GRU V4 asset-specific",
        "status": "EXPERIMENTAL",
        "coverage": list(SYMBOLS),
        "assets": assets,
    }


def get_symbol_model(symbol: str) -> dict | None:
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        return None
    summary = get_model_summary()
    return next(item for item in summary["assets"] if item["symbol"] == symbol)
