# RTA V4 Dashboard History Upgrade

This upgrade adds a professional historical context layer without filling MongoDB with old data.

## What changes

The dashboard now combines:

1. A compact 30-day historical reference stored as Parquet under `runtime_assets/history/`.
2. Live records from MongoDB from the moment the runtime starts.
3. Actual live GRU V4 prediction values, rendered as 15-minute experimental forecast markers.

No historical model predictions are invented.

## Files to replace / add

Copy this package into `E:\RTA_RUNTIME_V4` and allow matching files to be replaced.

Changed files:

- `api/routes/market.py`
- `api/services/market_service.py`
- `app/services/api_client.py`
- `app/ui/components.py`
- `app/main.py`

New files:

- `scripts/prepare_dashboard_history.py`
- `PREPARE_DASHBOARD_HISTORY.bat`

## One-time history preparation

After copying the code, run:

```bat
cd /d E:\RTA_RUNTIME_V4
conda activate pytorch_gpu
python scripts\prepare_dashboard_history.py --source "E:\crypto-rt-analytics" --days 30
```

or double-click:

```text
PREPARE_DASHBOARD_HISTORY.bat
```

This creates roughly 43,200 one-minute rows per asset, only for dashboard reference.
It does not modify MongoDB and does not copy the full historical training dataset.

## Restart

Restart FastAPI and Streamlit after the code replacement.
Spark does not need any change for this dashboard upgrade.

```bat
cd /d E:\RTA_RUNTIME_V4
conda activate pytorch_gpu
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Then:

```bat
cd /d E:\RTA_RUNTIME_V4
conda activate pytorch_gpu
streamlit run app\main.py
```

## API examples

```bat
curl "http://127.0.0.1:8000/market/BTCUSDT/history?period=30d&interval=auto&limit=1600"
curl "http://127.0.0.1:8000/market/ETHUSDT/history?period=7d&interval=auto&limit=1600"
```

Automatic chart intervals:

- 24 hours: 5-minute candles
- 7 days: 15-minute candles
- 30 days: 1-hour candles

The dashboard shows real period change, high and low values calculated from the stored historical reference plus current live stream.
