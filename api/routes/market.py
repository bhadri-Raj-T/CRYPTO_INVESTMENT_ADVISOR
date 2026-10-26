from fastapi import APIRouter, HTTPException, Query

from api.services.market_service import (
    get_latest_market_analytics,
    get_market_history,
    get_market_outlook,
    get_market_overview,
    get_market_symbol,
)

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/latest")
def latest_market():
    return get_latest_market_analytics()


@router.get("/overview")
def market_overview(
    period: str = Query("1d", pattern="^(1d|7d|30d)$"),
):
    return get_market_overview(period=period)


@router.get("/{symbol}/outlook")
def market_outlook(
    symbol: str,
    horizon_minutes: int = Query(60, ge=15, le=240),
):
    return get_market_outlook(symbol.upper(), horizon_minutes=horizon_minutes)


@router.get("/{symbol}/history")
def market_history(
    symbol: str,
    limit: int = Query(1200, ge=1, le=5000),
    period: str = Query("30d", pattern="^(1d|7d|30d)$"),
    interval: str = Query("auto", pattern="^(auto|1m|5m|15m|30m|1h|4h|1d)$"),
):
    return get_market_history(
        symbol.upper(),
        limit=limit,
        period=period,
        interval=interval,
    )


@router.get("/{symbol}")
def market_symbol(symbol: str):
    result = get_market_symbol(symbol.upper())
    if result is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return result
