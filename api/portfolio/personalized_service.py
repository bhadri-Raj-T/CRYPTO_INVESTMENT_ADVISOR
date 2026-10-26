from api.database import realtime_analytics_collection
from api.portfolio.portfolio_service import get_portfolio


SUPPORTED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]


def get_personalized_analytics(user_id, risk_tolerance):
    portfolio = get_portfolio(user_id)
    by_symbol = {holding["symbol"]: holding for holding in portfolio["holdings"]}
    assets = []

    for symbol in SUPPORTED_SYMBOLS:
        holding = by_symbol.get(symbol)
        latest = realtime_analytics_collection.find_one(
            {"symbol": symbol}, sort=[("timestamp", -1)]
        )
        prediction = latest.get("prediction") if latest else None
        risk = latest.get("risk") if latest else None
        anomaly = latest.get("anomaly") if latest else None
        market = latest.get("market") if latest else None

        base = {
            "symbol": symbol,
            "position_status": "HELD" if holding is not None else "MARKET_WATCH",
            "is_held": holding is not None,
            "prediction": prediction,
            "risk": risk,
            "anomaly": anomaly,
            "market": market,
            "personalized_context": {
                "risk_tolerance": risk_tolerance,
                "market_data_available": latest is not None,
                "portfolio_position": holding is not None,
            },
        }
        if holding is not None:
            base.update(holding)
        else:
            base.update(
                {
                    "quantity": 0.0,
                    "average_cost": 0.0,
                    "cost_basis": 0.0,
                    "current_price": float((market or {}).get("close", 0.0) or 0.0),
                    "current_value": 0.0,
                    "unrealized_pnl": 0.0,
                    "pnl_percent": 0.0,
                    "total_fees": 0.0,
                }
            )
        assets.append(base)

    return {
        "username": None,
        "risk_tolerance": risk_tolerance,
        "assets": assets,
        "portfolio_summary": portfolio["portfolio_summary"],
    }
