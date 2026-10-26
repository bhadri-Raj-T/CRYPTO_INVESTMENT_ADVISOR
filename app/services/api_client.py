import os
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_TIMEOUT = 10


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def get_market_latest():
    response = requests.get(f"{API_BASE_URL}/market/latest", timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_market_overview(period="1d"):
    response = requests.get(
        f"{API_BASE_URL}/market/overview",
        params={"period": period},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_market_outlook(symbol, horizon_minutes=60):
    response = requests.get(
        f"{API_BASE_URL}/market/{symbol}/outlook",
        params={"horizon_minutes": horizon_minutes},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_market(symbol):
    response = requests.get(f"{API_BASE_URL}/market/{symbol}", timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_market_history(symbol, limit=1200, period="30d", interval="auto"):
    response = requests.get(
        f"{API_BASE_URL}/market/{symbol}/history",
        params={"limit": limit, "period": period, "interval": interval},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def register_user(username, password):
    return requests.post(
        f"{API_BASE_URL}/auth/register",
        json={"username": username, "password": password},
        timeout=DEFAULT_TIMEOUT,
    )


def login_user(username, password):
    return requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": username, "password": password},
        timeout=DEFAULT_TIMEOUT,
    )


def get_current_user(token):
    return requests.get(
        f"{API_BASE_URL}/auth/me",
        headers=_auth_headers(token),
        timeout=DEFAULT_TIMEOUT,
    )


def get_portfolio(token):
    return requests.get(
        f"{API_BASE_URL}/portfolio",
        headers=_auth_headers(token),
        timeout=DEFAULT_TIMEOUT,
    )


def create_transaction(token, symbol, side, quantity, price, fees=0.0):
    return requests.post(
        f"{API_BASE_URL}/portfolio/transactions",
        headers=_auth_headers(token),
        json={
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "fees": fees,
        },
        timeout=DEFAULT_TIMEOUT,
    )


def get_personalized_analytics(token):
    return requests.get(
        f"{API_BASE_URL}/portfolio/analytics",
        headers=_auth_headers(token),
        timeout=DEFAULT_TIMEOUT,
    )


def get_recommendations(token):
    return requests.get(
        f"{API_BASE_URL}/portfolio/recommendations",
        headers=_auth_headers(token),
        timeout=DEFAULT_TIMEOUT,
    )


def get_alerts(token, unread_only=False, limit=50):
    return requests.get(
        f"{API_BASE_URL}/alerts",
        headers=_auth_headers(token),
        params={"unread_only": unread_only, "limit": limit},
        timeout=DEFAULT_TIMEOUT,
    )


def generate_alerts(token):
    return requests.post(
        f"{API_BASE_URL}/alerts/generate",
        headers=_auth_headers(token),
        timeout=DEFAULT_TIMEOUT,
    )


def mark_alert_read(token, alert_id):
    return requests.post(
        f"{API_BASE_URL}/alerts/{alert_id}/read",
        headers=_auth_headers(token),
        timeout=DEFAULT_TIMEOUT,
    )


def get_risk_profile(token):
    return requests.get(
        f"{API_BASE_URL}/profile/risk",
        headers=_auth_headers(token),
        timeout=DEFAULT_TIMEOUT,
    )


def update_risk_profile(token, risk_tolerance):
    return requests.put(
        f"{API_BASE_URL}/profile/risk",
        headers=_auth_headers(token),
        json={"risk_tolerance": risk_tolerance},
        timeout=DEFAULT_TIMEOUT,
    )


def get_model_summary():
    response = requests.get(f"{API_BASE_URL}/models/summary", timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_model_comparison():
    response = requests.get(f"{API_BASE_URL}/models/comparison", timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_symbol_model(symbol):
    response = requests.get(f"{API_BASE_URL}/models/{symbol}", timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()
