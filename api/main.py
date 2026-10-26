from fastapi import FastAPI

from api.mongo_schema import create_realtime_analytics_indexes
from api.routes import alerts, auth, health, market, models, portfolio, profile

app = FastAPI(
    title="RTA API",
    version="4.0.0",
    description="Runtime API for RTA real-time crypto analytics and GRU V4 predictions.",
)

create_realtime_analytics_indexes()
app.include_router(health.router)
app.include_router(market.router)
app.include_router(models.router)
app.include_router(auth.router)
app.include_router(portfolio.router)
app.include_router(alerts.router)
app.include_router(profile.router)


@app.get("/")
def root():
    return {
        "message": "RTA V4 API is running",
        "status": "ok",
        "model": "GRU V4 asset-specific",
        "assets": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
    }
