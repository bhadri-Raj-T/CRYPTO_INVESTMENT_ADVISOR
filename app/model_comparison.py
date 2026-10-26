from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = PROJECT_ROOT / "runtime_assets" / "reports" / "comparison_report.json"
SUPPORTED_ASSETS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]


def load_comparison_results() -> dict[str, Any]:
    if not RESULTS_PATH.exists():
        return {}
    try:
        payload = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def comparison_rows(payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = payload if payload is not None else load_comparison_results()
    rows: list[dict[str, Any]] = []
    specs = [
        ("GRU V4", "gru_v4", "direction_accuracy", "direction_auc", "prediction_target_correlation"),
        ("XGBoost", "xgboost", "direction_accuracy", None, "correlation"),
        ("Chronos-2", "chronos2", "direction_accuracy", None, "correlation"),
    ]
    for symbol in SUPPORTED_ASSETS:
        for model_name, key, direction_key, auc_key, corr_key in specs:
            metrics = (payload.get(key) or {}).get(symbol)
            if not isinstance(metrics, dict):
                continue
            rows.append({
                "Asset": symbol,
                "Model": model_name,
                "R²": metrics.get("r2"),
                "RMSE": metrics.get("rmse"),
                "Direction accuracy": metrics.get(direction_key),
                "AUC": metrics.get(auc_key) if auc_key else None,
                "Correlation": metrics.get(corr_key),
            })
    return rows
