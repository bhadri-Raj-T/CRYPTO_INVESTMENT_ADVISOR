"""Runtime-safe facts for the final RTA GRU V4 deployment."""

MODEL_NAME = "GRU V4 Asset-Specific"
MODEL_STATUS = "Experimental"
SUPPORTED_ASSETS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
SEQUENCE_LENGTH = 60
FORECAST_HORIZON_MINUTES = 15
FEATURES_PER_MODEL = 50
MODEL_COUNT = 4

ARCHITECTURE = [
    "LayerNorm(50)",
    "2-layer GRU · hidden 192 · dropout 0.2",
    "Attention pooling",
    "LayerNorm(192)",
    "Linear 192 → 128 → GELU → Dropout",
    "Return head 128 → 64 → 1",
    "Direction head 128 → 64 → 1",
]

RISK_ENGINE = {
    "name": "RISK_ENGINE_V1",
    "weights": {
        "Volatility": 0.30,
        "ATR": 0.25,
        "Range": 0.15,
        "Volume": 0.15,
        "Order Flow": 0.15,
    },
    "levels": "LOW 0–33.33 · MEDIUM 33.33–66.67 · HIGH 66.67–100",
}

ANOMALY_ENGINE = {
    "name": "ISOLATION_FOREST_V1",
    "feature_count": 50,
    "n_estimators": 200,
    "contamination": 0.05,
    "random_state": 42,
}
