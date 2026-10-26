# RTA Review Dashboard - Screen Recording Guide

## What this build changes

The dashboard now makes the prediction layer visually explicit:

1. **Gold +15m point = direct GRU V4 model output.**
2. **Purple +30m / +45m / +60m path = scenario extension only.** It is not presented as extra trained model predictions.
3. The dashboard explains that a new direct prediction is generated after a new **closed 1-minute candle** reaches the pipeline.
4. A four-asset market scanner shows BTC, ETH, BNB and SOL together.
5. Advisor recommendations cover all four assets even when the user holds none of them. Holdings add context; they are no longer a requirement.

## Recommended recording sequence

1. Start infrastructure, producer, Spark, FastAPI and Streamlit.
2. Open **Dashboard**.
3. Show the four asset cards and the green **LIVE PIPELINE** banner.
4. Select BTC, then ETH, to show that each asset has its own current forecast.
5. Point to the five top cards: live price, +15m model price, forecast move, direction/P(up), risk.
6. On the main chart, explain:
   - historical line = context,
   - live line = current stream,
   - gold diamond = direct +15m GRU V4 prediction,
   - purple dashed line = one-hour scenario visualization.
7. Scroll to **Forecast horizon** and show that the table says MODEL only for +15m and SCENARIO for later horizons.
8. Show the four-asset market scanner.
9. Sign in and show **Market advisor preview** or open **Advisor**. It now shows all supported assets even with an empty portfolio.

## Suggested review sentence

> The current GRU V4 is trained for a 15-minute horizon. Every new closed one-minute candle can create a new +15-minute target, so over time we build a live forecast tape. For the review dashboard I also show a clearly labelled one-hour scenario extension, but I do not claim those later points are separately trained predictions.

## Accuracy note

Do not describe +30m, +45m or +60m as model predictions. The research phase should train explicit multi-horizon targets if those horizons are required scientifically.
