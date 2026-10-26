# Dashboard Review Upgrade

## Added
- `/market/overview?period=1d` compact four-asset endpoint.
- `/market/{symbol}/outlook?horizon_minutes=60` endpoint.
- Prominent direct +15m model forecast cards.
- Forecast target timestamp and inference-trigger explanation.
- One-hour scenario visualization with explicit MODEL vs SCENARIO labels.
- Four-asset live scanner with data freshness.
- Market-wide advisor support even when the portfolio is empty.
- Screen-recording review guide.

## Preserved
- GRU V4 trained horizon remains 15 minutes.
- Existing risk and anomaly engines are unchanged.
- Existing history API and historical/live separation are preserved.
- No new model weights are fabricated or required by this dashboard change.
