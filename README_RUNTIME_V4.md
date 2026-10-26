# RTA V4 Lightweight Runtime

This folder is the deployment/runtime version of the RTA project after the final four-asset GRU V4 training run.

It intentionally does **not** contain the historical training datasets, processed NumPy arrays, training scripts, epoch logs, or model-development code.

## Final runtime architecture

```text
Binance WebSocket
        ↓
Kafka
        ↓
Spark Structured Streaming
        ↓
Exact V4 feature engineering
        ↓
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ BTC GRU V4   │ ETH GRU V4   │ BNB GRU V4   │ SOL GRU V4   │
│ 60 × 50      │ 60 × 50      │ 60 × 50      │ 60 × 50      │
└──────────────┴──────────────┴──────────────┴──────────────┘
        ↓
Risk + anomaly analytics
        ↓
MongoDB
        ↓
FastAPI
        ↓
Streamlit
```

The older GRU V3 `60 × 200 → BTC only` inference path is not used by this runtime.

## What is included

```text
RTA_RUNTIME_V4/
├── producer/                 Binance → Kafka
├── streaming/                Spark + V4 four-model inference
├── analytics/                Risk + anomaly engines
├── api/                      FastAPI, auth, portfolio, advisor, alerts
├── app/                      Final professional Streamlit frontend
├── runtime_assets/
│   ├── models/               Created by preparation script
│   ├── bootstrap/            240 recent candles/asset only
│   └── reports/              Final comparison report
├── scripts/
│   └── prepare_runtime_assets.py
├── PREPARE_RUNTIME_ASSETS.bat
├── RUN_1_INFRA.bat
├── RUN_2_PRODUCER.bat
├── RUN_3_SPARK_V4.bat
├── RUN_4_FASTAPI.bat
├── RUN_5_STREAMLIT.bat
└── RUN_MODEL_REVIEW.bat
```

## One-time setup

Extract this runtime ZIP to a **new folder**, for example:

```text
E:\RTA_RUNTIME_V4
```

Keep your completed training project at:

```text
E:\crypto-rt-analytics
```

Then run:

```bat
cd /d E:\RTA_RUNTIME_V4
conda activate pytorch_gpu
python scripts\prepare_runtime_assets.py --source "E:\crypto-rt-analytics"
```

Or double-click:

```text
PREPARE_RUNTIME_ASSETS.bat
```

The preparation script copies only the deployment artifacts:

```text
training\models\gru_v4\BTCUSDT\best_model_v4.pt
training\models\gru_v4\ETHUSDT\best_model_v4.pt
training\models\gru_v4\BNBUSDT\best_model_v4.pt
training\models\gru_v4\SOLUSDT\best_model_v4.pt
```

plus each asset's `scaler.joblib`, optional result JSON, and only the latest 240 raw candles for startup feature warm-up.

After this one-time step, the runtime does not need the full historical training data.

## Start the product

Open five Command Prompt windows.

### Terminal 1: Kafka + MongoDB

```bat
cd /d E:\RTA_RUNTIME_V4
docker compose up -d
docker compose ps
```

Or run `RUN_1_INFRA.bat`.

### Terminal 2: Binance producer

```bat
cd /d E:\RTA_RUNTIME_V4
conda activate pytorch_gpu
python -m producer.run_producer
```

Or run `RUN_2_PRODUCER.bat`.

### Terminal 3: Spark + four GRU V4 models

```bat
cd /d E:\RTA_RUNTIME_V4
conda activate pytorch_gpu
set RTA_INFERENCE_DEVICE=cpu
python -m streaming.spark_session
```

Or run `RUN_3_SPARK_V4.bat`.

CPU inference is the default recommendation for the live runtime because only four small sequences are inferred once per closed one-minute candle. It leaves the RTX GPU free and avoids the Windows CUDA shutdown behaviour encountered during training. To test GPU inference, set `RTA_INFERENCE_DEVICE=cuda`.

### Terminal 4: FastAPI

```bat
cd /d E:\RTA_RUNTIME_V4
conda activate pytorch_gpu
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Or run `RUN_4_FASTAPI.bat`.

Useful tests:

```bat
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/market/latest
curl http://127.0.0.1:8000/models/summary
curl http://127.0.0.1:8000/models/comparison
```

### Terminal 5: Streamlit

```bat
cd /d E:\RTA_RUNTIME_V4
conda activate pytorch_gpu
streamlit run app\main.py
```

Or run `RUN_5_STREAMLIT.bat`.

Default URL:

```text
http://localhost:8501
```

## What changed from the earlier runtime

### Spark

Old:

```text
BTC + ETH + BNB + SOL
50 features each
        ↓
60 × 200 aligned matrix
        ↓
BTC-only GRU V3
```

New:

```text
BTC → 60 × 50 → BTC GRU V4
ETH → 60 × 50 → ETH GRU V4
BNB → 60 × 50 → BNB GRU V4
SOL → 60 × 50 → SOL GRU V4
```

Each model uses the matching train-only `StandardScaler` from its V4 dataset preparation.

### MongoDB

Every latest market document can now contain a V4 prediction for its own symbol:

```json
{
  "prediction": {
    "value": 0.0001,
    "predicted_log_return": 0.0001,
    "direction": "UP",
    "return_direction": "UP",
    "probability_up": 0.53,
    "probability_down": 0.47,
    "confidence": 0.53,
    "signal": "NEUTRAL",
    "source": "GRU_V4_ASSET_SPECIFIC_EXPERIMENTAL",
    "model_version": "GRU_V4",
    "forecast_horizon_minutes": 15,
    "status": "OK"
  }
}
```

### FastAPI

Existing market, auth, portfolio, advisor and alert contracts are retained.

New public endpoints:

```text
GET /models/summary
GET /models/comparison
GET /models/{symbol}
```

### Streamlit

The public Dashboard now shows the experimental V4 forecast for BTC, ETH, BNB and SOL. The About → Model evaluation tab shows the final GRU V4 results and the GRU/XGBoost/Chronos-2 comparison.

## Standalone model review page

For the academic review:

```bat
streamlit run app\model_review.py
```

or run `RUN_MODEL_REVIEW.bat`.

## Data honesty

The V4 models remain experimental. The runtime deliberately keeps that wording. Near-zero or negative R² on the 15-minute return target is not hidden. The UI reports multiple metrics rather than claiming high predictive accuracy.
