"""RTA GRU V4 multi-asset runtime inference.

Loads one trained V4 checkpoint and one train-only feature scaler per asset.
This module is inference-only. No training package is required at runtime.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import torch
import torch.nn as nn

from streaming.features import get_feature_columns

LOGGER = logging.getLogger("gru_v4_inference")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = Path(os.getenv("RTA_MODEL_ROOT", str(PROJECT_ROOT / "runtime_assets" / "models")))
SUPPORTED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT")
DEFAULT_DEVICE = os.getenv("RTA_INFERENCE_DEVICE", "cpu").strip().lower()
SEQ_LEN = 60
FEATURE_COUNT = 50
FORECAST_HORIZON_MINUTES = 15
MODEL_SOURCE = "GRU_V4_ASSET_SPECIFIC_EXPERIMENTAL"


class AttentionPooling(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        mid = max(32, hidden_size // 2)
        self.score = nn.Sequential(
            nn.Linear(hidden_size, mid),
            nn.Tanh(),
            nn.Linear(mid, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weights = torch.softmax(self.score(x).squeeze(-1), dim=1)
        return torch.sum(x * weights.unsqueeze(-1), dim=1)


class AssetGRUV4(nn.Module):
    """Exact architecture used by the final V4 checkpoints."""

    def __init__(
        self,
        input_size: int = 50,
        hidden_size: int = 192,
        num_layers: int = 2,
        dropout: float = 0.20,
    ):
        super().__init__()
        self.input_norm = nn.LayerNorm(input_size)
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.attention = AttentionPooling(hidden_size)
        self.post_norm = nn.LayerNorm(hidden_size)
        self.shared = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.return_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
        )
        self.direction_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor):
        x = self.input_norm(x)
        sequence, _ = self.gru(x)
        pooled = self.attention(sequence)
        pooled = self.post_norm(pooled)
        shared = self.shared(pooled)
        return (
            self.return_head(shared).squeeze(-1),
            self.direction_head(shared).squeeze(-1),
        )


def _resolve_device(requested: str | None = None) -> torch.device:
    requested = (requested or DEFAULT_DEVICE).lower()
    if requested == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    if requested == "cuda" and not torch.cuda.is_available():
        LOGGER.warning("RTA_INFERENCE_DEVICE=cuda requested, but CUDA is unavailable. Falling back to CPU.")
    return torch.device("cpu")


class GRUV4Predictor:
    def __init__(self, symbol: str, device: str | None = None):
        symbol = symbol.upper()
        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported symbol: {symbol}")

        self.symbol = symbol
        self.device = _resolve_device(device)
        self.asset_dir = MODEL_ROOT / symbol
        self.checkpoint_path = self.asset_dir / "best_model_v4.pt"
        self.scaler_path = self.asset_dir / "scaler.joblib"

        if not self.checkpoint_path.exists():
            raise FileNotFoundError(f"Missing V4 checkpoint: {self.checkpoint_path}")
        if not self.scaler_path.exists():
            raise FileNotFoundError(f"Missing V4 scaler: {self.scaler_path}")

        checkpoint = torch.load(
            self.checkpoint_path,
            map_location=self.device,
            weights_only=False,
        )
        cfg = checkpoint.get("model_config", {})

        self.seq_len = int(cfg.get("seq_len", SEQ_LEN))
        self.input_size = int(cfg.get("input_size", FEATURE_COUNT))
        self.horizon_minutes = int(cfg.get("forecast_horizon_minutes", FORECAST_HORIZON_MINUTES))
        self.target_mean = float(checkpoint["target_mean"])
        self.target_std = float(checkpoint["target_std"])
        self.feature_names = list(checkpoint.get("feature_names") or get_feature_columns())

        expected_features = get_feature_columns()
        if self.input_size != FEATURE_COUNT:
            raise RuntimeError(f"{symbol}: checkpoint input_size={self.input_size}, expected {FEATURE_COUNT}")
        if self.seq_len != SEQ_LEN:
            raise RuntimeError(f"{symbol}: checkpoint seq_len={self.seq_len}, expected {SEQ_LEN}")
        if self.feature_names and self.feature_names != expected_features:
            raise RuntimeError(f"{symbol}: feature order in checkpoint does not match streaming feature contract")

        self.scaler = joblib.load(self.scaler_path)
        self.model = AssetGRUV4(
            input_size=self.input_size,
            hidden_size=int(cfg.get("hidden_size", 192)),
            num_layers=int(cfg.get("num_layers", 2)),
            dropout=float(cfg.get("dropout", 0.20)),
        ).to(self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"], strict=True)
        self.model.eval()

        LOGGER.info(
            "Loaded GRU V4 | symbol=%s | device=%s | seq=%d | features=%d | horizon=%dm",
            self.symbol,
            self.device,
            self.seq_len,
            self.input_size,
            self.horizon_minutes,
        )

    @torch.inference_mode()
    def predict(self, raw_feature_sequence: Any) -> dict[str, Any]:
        x = np.asarray(raw_feature_sequence, dtype=np.float32)
        expected_shape = (self.seq_len, self.input_size)
        if x.shape != expected_shape:
            raise ValueError(f"{self.symbol}: expected sequence {expected_shape}, got {x.shape}")
        if not np.isfinite(x).all():
            raise ValueError(f"{self.symbol}: input sequence contains NaN/Inf")

        scaled = self.scaler.transform(x).astype(np.float32, copy=False)
        tensor = torch.from_numpy(scaled).unsqueeze(0).to(self.device)
        predicted_scaled_return, direction_logit = self.model(tensor)

        predicted_return = float(
            predicted_scaled_return.item() * self.target_std + self.target_mean
        )
        probability_up = float(torch.sigmoid(direction_logit).item())
        probability_down = 1.0 - probability_up
        direction = "UP" if probability_up >= 0.5 else "DOWN"
        return_direction = "UP" if predicted_return >= 0.0 else "DOWN"

        if probability_up >= 0.55:
            signal = "BULLISH"
        elif probability_up <= 0.45:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        return {
            "value": predicted_return,
            "predicted_log_return": predicted_return,
            "direction": direction,
            "return_direction": return_direction,
            "probability_up": probability_up,
            "probability_down": probability_down,
            "confidence": max(probability_up, probability_down),
            "signal": signal,
            "source": MODEL_SOURCE,
            "model_version": "GRU_V4",
            "forecast_horizon_minutes": self.horizon_minutes,
            "status": "OK",
        }


_PREDICTORS: dict[str, GRUV4Predictor] = {}


def get_predictor(symbol: str) -> GRUV4Predictor:
    symbol = symbol.upper()
    predictor = _PREDICTORS.get(symbol)
    if predictor is None:
        predictor = GRUV4Predictor(symbol)
        _PREDICTORS[symbol] = predictor
    return predictor


def warmup_models() -> dict[str, str]:
    """Load all four checkpoints once at streaming startup."""
    status: dict[str, str] = {}
    for symbol in SUPPORTED_SYMBOLS:
        try:
            get_predictor(symbol)
            status[symbol] = "READY"
        except Exception as exc:
            LOGGER.exception("Unable to load %s GRU V4", symbol)
            status[symbol] = f"ERROR: {exc}"
    return status


def predict_gru(symbol: str, raw_feature_sequence: Any) -> dict[str, Any]:
    return get_predictor(symbol).predict(raw_feature_sequence)


def model_runtime_status() -> dict[str, dict[str, Any]]:
    result = {}
    for symbol in SUPPORTED_SYMBOLS:
        asset_dir = MODEL_ROOT / symbol
        result[symbol] = {
            "checkpoint": str(asset_dir / "best_model_v4.pt"),
            "checkpoint_exists": (asset_dir / "best_model_v4.pt").exists(),
            "scaler": str(asset_dir / "scaler.joblib"),
            "scaler_exists": (asset_dir / "scaler.joblib").exists(),
            "loaded": symbol in _PREDICTORS,
        }
    return result
