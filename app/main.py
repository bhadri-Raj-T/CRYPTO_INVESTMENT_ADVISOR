from __future__ import annotations

import math
import time

import pandas as pd
import plotly.express as px
import streamlit as st

from model_comparison import comparison_rows, load_comparison_results
from model_info import ANOMALY_ENGINE, ARCHITECTURE, RISK_ENGINE
from services.api_client import (
    create_transaction,
    generate_alerts,
    get_alerts,
    get_current_user,
    get_market_history,
    get_market_latest,
    get_market_outlook,
    get_market_overview,
    get_model_comparison,
    get_personalized_analytics,
    get_portfolio,
    get_recommendations,
    get_risk_profile,
    login_user,
    mark_alert_read,
    register_user,
    update_risk_profile,
)
from services.session import (
    get_token,
    get_username,
    initialize_session,
    is_authenticated,
    login_user as save_login,
    logout_user,
)
from ui.components import (
    SYMBOL_NAMES,
    api_error,
    empty_state,
    history_dataframe,
    login_cta,
    market_card,
    metric_card,
    money,
    normalize_record,
    page_heading,
    parse_time,
    pct,
    price_chart,
    prediction_timeline,
    risk_gauge,
    safe_float,
    section,
    short_price,
    signal_row,
    status_label,
    window_change,
)
from ui.theme import inject_theme


SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
PUBLIC_NAV = ["Dashboard", "About"]
PRIVATE_NAV = ["Dashboard", "Markets", "Portfolio", "Advisor", "Alerts", "About"]
PRIVATE_PAGES = {"Markets", "Portfolio", "Advisor", "Alerts"}

st.set_page_config(
    page_title="RTA | Crypto Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_theme()
initialize_session()
st.session_state.setdefault("advisor_view", "Recommendations")
st.session_state.setdefault("portfolio_view", "Overview")
st.session_state.setdefault("dashboard_asset", "BTCUSDT")
st.session_state.setdefault("dashboard_period", "30d")


def response_detail(response, fallback: str) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get("detail", fallback))
    except Exception:
        pass
    return fallback


def _brand_html() -> str:
    return """
    <div class="rta-brand-wrap">
      <div class="rta-mark">R</div>
      <div><div class="rta-brand">RTA</div><div class="rta-brand-sub">Crypto Intelligence</div></div>
    </div>
    """


def _go(page: str):
    st.session_state["active_page"] = page
    st.rerun()


def render_auth_popover():
    if is_authenticated():
        with st.popover(f"{get_username() or 'Account'}  ▾", use_container_width=True):
            st.caption("Signed in")
            st.markdown(f"**{get_username() or 'User'}**")
            if st.button("Portfolio", key="account_portfolio", use_container_width=True):
                _go("Portfolio")
            if st.button("Risk profile", key="account_risk", use_container_width=True):
                st.session_state["advisor_view"] = "Risk Profile"
                _go("Advisor")
            st.divider()
            if st.button("Log out", key="logout_top", use_container_width=True):
                logout_user()
                st.rerun()
        return

    with st.popover("Log in", use_container_width=True):
        sign_in, create = st.tabs(["Sign in", "Create account"])
        with sign_in:
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                if not username.strip() or not password:
                    st.error("Enter your username and password.")
                else:
                    try:
                        response = login_user(username.strip(), password)
                        if response.status_code == 200:
                            token = response.json().get("access_token")
                            if not token:
                                st.error("The API did not return an access token.")
                            else:
                                me = get_current_user(token)
                                if me.status_code == 200:
                                    user = me.json()
                                    save_login(token, user.get("username", username.strip()), user.get("id", user.get("_id", "")))
                                    st.session_state["active_page"] = "Dashboard"
                                    st.rerun()
                                else:
                                    st.error("Login succeeded, but user verification failed.")
                        else:
                            st.error(response_detail(response, "Login failed."))
                    except Exception as exc:
                        api_error("FastAPI is not reachable. Start the API and try again.", exc)
        with create:
            with st.form("register_form"):
                new_username = st.text_input("Username", key="register_username")
                new_password = st.text_input("Password", type="password", key="register_password")
                confirm = st.text_input("Confirm password", type="password", key="register_confirm")
                created = st.form_submit_button("Create account", use_container_width=True)
            if created:
                if not new_username.strip() or not new_password:
                    st.error("Username and password are required.")
                elif new_password != confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        response = register_user(new_username.strip(), new_password)
                        if response.status_code in (200, 201):
                            st.success("Account created. Sign in to continue.")
                        else:
                            st.error(response_detail(response, "Registration failed."))
                    except Exception as exc:
                        api_error("FastAPI is not reachable. Start the API and try again.", exc)


def render_header() -> str:
    nav_items = PRIVATE_NAV if is_authenticated() else PUBLIC_NAV
    current = st.session_state.get("active_page", "Dashboard")
    if current in PRIVATE_PAGES and not is_authenticated():
        current = "Dashboard"
        st.session_state["active_page"] = current

    brand_col, nav_col, auth_col = st.columns([2.15, 6.9, 1.25])
    with brand_col:
        st.markdown(_brand_html(), unsafe_allow_html=True)
    with nav_col:
        if is_authenticated():
            nav_cols = st.columns(len(nav_items))
        else:
            public_cols = st.columns([1.05, 1.05, 3.6])
            nav_cols = public_cols[:2]
        for col, page in zip(nav_cols, nav_items):
            with col:
                if st.button(
                    page,
                    key=f"nav_{page}",
                    type="primary" if current == page else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["active_page"] = page
                    st.rerun()
    with auth_col:
        render_auth_popover()
    st.markdown("<div class='rta-top-rule'></div>", unsafe_allow_html=True)
    return st.session_state.get("active_page", "Dashboard")


def fetch_latest() -> tuple[list[dict], str | None]:
    try:
        payload = get_market_latest()
        return payload.get("data", []), None
    except Exception as exc:
        return [], str(exc)


def market_map(rows: list[dict]) -> dict[str, dict]:
    normalized = [normalize_record(item) for item in rows]
    return {str(item.get("symbol")): item for item in normalized if item.get("symbol")}


def render_asset_strip(rows: list[dict]):
    by_symbol = market_map(rows)
    cols = st.columns(4)
    for col, symbol in zip(cols, SYMBOLS):
        with col:
            market_card(symbol, by_symbol.get(symbol, {}))


def render_dashboard():
    page_heading(
        "Real-time crypto forecast console",
        "Live stream status, direct GRU V4 +15m prediction, one-hour review scenario and four-asset market intelligence.",
        "Live review",
    )

    rows, error = fetch_latest()
    if error:
        api_error(
            "Live market data is unavailable. Start FastAPI and the streaming pipeline for live values.",
            error,
        )
        return

    by_symbol = market_map(rows)
    render_asset_strip(rows)

    section("Review controls", "Choose an asset, context window and dashboard refresh rate.")
    asset_area, period_area, refresh_area = st.columns([4.8, 2.0, 1.8])
    with asset_area:
        asset_cols = st.columns(4)
        for col, symbol in zip(asset_cols, SYMBOLS):
            with col:
                if st.button(
                    symbol.replace("USDT", ""),
                    key=f"dash_asset_{symbol}",
                    type="primary" if st.session_state["dashboard_asset"] == symbol else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["dashboard_asset"] = symbol
                    st.rerun()
    with period_area:
        period = st.selectbox(
            "Context",
            options=["1d", "7d", "30d"],
            index=["1d", "7d", "30d"].index(st.session_state.get("dashboard_period", "30d")),
            format_func=lambda value: {"1d": "24 hours", "7d": "7 days", "30d": "30 days"}[value],
            label_visibility="collapsed",
            key="dashboard_period_select",
        )
        st.session_state["dashboard_period"] = period
    with refresh_area:
        refresh_seconds = st.selectbox(
            "Refresh",
            [0, 5, 10, 30],
            index=1,
            format_func=lambda value: "Manual" if value == 0 else f"Auto · {value}s",
            label_visibility="collapsed",
            key="dashboard_refresh_seconds",
        )

    symbol = st.session_state.get("dashboard_asset", "BTCUSDT")
    selected = by_symbol.get(symbol, {})
    risk = selected.get("risk") or {}
    anomaly = selected.get("anomaly") or {}
    prediction = selected.get("prediction") or {}

    try:
        history_payload = get_market_history(symbol, limit=1800, period=period, interval="auto")
        history = history_dataframe(history_payload)
        stats = history_payload.get("stats") or {}
    except Exception as exc:
        history_payload = {}
        history = pd.DataFrame()
        stats = {}
        st.warning(f"Historical context unavailable: {exc}")

    try:
        outlook = get_market_outlook(symbol, horizon_minutes=60)
    except Exception as exc:
        outlook = {}
        st.warning(f"Forecast horizon unavailable: {exc}")

    try:
        overview_payload = get_market_overview("1d")
        overview_rows = overview_payload.get("data", [])
    except Exception:
        overview_payload = {}
        overview_rows = []

    direct = outlook.get("direct_forecast") or {}
    live_price = selected.get("close", outlook.get("current_price"))
    forecast_price = direct.get("price")
    forecast_move = direct.get("move_percent")
    probability_up = outlook.get("probability_up", prediction.get("probability_up"))
    direction = outlook.get("direction", prediction.get("direction"))

    # Prominent review strip: makes the model output visible immediately in recordings.
    st.markdown(
        "<div class='rta-forecast-banner'><div><span class='rta-live-pulse'></span>LIVE PIPELINE</div>"
        "<div class='rta-forecast-banner-main'>GRU V4 direct model horizon: <b>+15 minutes</b></div>"
        "<div class='rta-forecast-banner-sub'>New direct inference is produced when a new closed 1-minute candle reaches the feature pipeline.</div></div>",
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        metric_card("Live price", short_price(live_price), f"{SYMBOL_NAMES.get(symbol, symbol)} · USDT", "accent")
    with m2:
        metric_card(
            "+15m model price",
            short_price(forecast_price) if forecast_price is not None else "Warming up",
            "DIRECT GRU V4 OUTPUT",
            "warning" if forecast_price is not None else "neutral",
        )
    with m3:
        metric_card(
            "Forecast move",
            "Unavailable" if forecast_move is None else f"{safe_float(forecast_move):+.3f}%",
            "Current → +15m model target",
            "success" if forecast_move is not None and safe_float(forecast_move) >= 0 else "danger" if forecast_move is not None else "neutral",
        )
    with m4:
        metric_card(
            "Direction / P(up)",
            status_label(direction) if direction else "Warming up",
            "Unavailable" if probability_up is None else f"P(up) {safe_float(probability_up) * 100:.1f}%",
        )
    with m5:
        metric_card(
            "Market risk",
            status_label(risk.get("level")),
            f"Score {safe_float(risk.get('score')):.1f}/100",
            "danger" if str(risk.get("level", "")).upper() == "HIGH" else "neutral",
        )

    chart_col, intelligence_col = st.columns([1.78, .82])
    with chart_col:
        st.markdown("<div class='rta-panel'>", unsafe_allow_html=True)
        h1, h2 = st.columns([3.5, 1.1])
        with h1:
            st.markdown(f"**{SYMBOL_NAMES.get(symbol, symbol)} · {symbol.replace('USDT', '')}/USDT live + forecast**")
            st.caption("Historical context + current stream + actual +15m GRU forecast tape + review scenario")
        with h2:
            st.caption(f"Latest stream · {parse_time(selected.get('timestamp'))}")
        price_chart(
            history,
            symbol,
            prediction=prediction,
            current_price=live_price,
            current_timestamp=selected.get("timestamp"),
            outlook=outlook,
            height=455,
        )
        st.markdown(
            "<div class='rta-legend-note'><b>Gold diamond:</b> direct +15m GRU V4 forecast. "
            "<b>Purple dashed path:</b> +30/+45/+60m scenario extension for review visualization, not additional trained model outputs.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with intelligence_col:
        st.markdown("<div class='rta-panel'>", unsafe_allow_html=True)
        st.markdown("**Prediction processing**")
        st.caption("Current model state and inference trigger")
        signal_row("Model", "GRU V4", "Asset-specific 60 × 50 sequence")
        signal_row("Direct horizon", "+15 minutes", "Trained target")
        signal_row("Inference trigger", "Closed 1m candle", "No repeated fake inference between candles")
        signal_row("Model direction", status_label(direction), "Latest valid output")
        if probability_up is not None:
            signal_row("Probability up", f"{safe_float(probability_up) * 100:.1f}%", "Experimental probability")
        signal_row(
            "Anomaly",
            "FLAGGED" if anomaly.get("is_anomaly") else "NORMAL",
            f"Score {safe_float(anomaly.get('score')):.3f}",
        )
        if direct.get("timestamp"):
            signal_row("+15m target time", parse_time(direct.get("timestamp")), "Forecast target")
        st.markdown("</div>", unsafe_allow_html=True)

    section(
        "Forecast horizon",
        "The trained +15m prediction is separated from the one-hour visualization scenario so the review remains technically accurate.",
    )
    timeline_col, table_col = st.columns([1.55, 1.0])
    with timeline_col:
        prediction_timeline(outlook, height=300)
    with table_col:
        points = outlook.get("points", []) if isinstance(outlook, dict) else []
        if points:
            table_rows = []
            for point in points:
                if point.get("horizon_minutes", 0) == 0:
                    continue
                table_rows.append(
                    {
                        "Horizon": f"+{point.get('horizon_minutes')}m",
                        "Type": "MODEL" if point.get("kind") == "DIRECT_MODEL" else "SCENARIO",
                        "Target UTC": parse_time(point.get("timestamp")),
                        "Price": short_price(point.get("price")),
                        "Move": f"{safe_float(point.get('move_percent')):+.3f}%",
                    }
                )
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        st.info(
            "For the review: only +15m is a trained GRU V4 prediction. The +30m, +45m and +60m points are a decaying scenario continuation. A future research model should train those horizons directly."
        )

    section("Four-asset market scanner", "Current stream status across BTC, ETH, BNB and SOL.")
    if overview_rows:
        scanner = []
        for row in overview_rows:
            age = row.get("age_seconds")
            if age is None:
                freshness = "Unavailable"
            elif age < 90:
                freshness = f"LIVE · {int(age)}s"
            elif age < 3600:
                freshness = f"{int(age // 60)}m old"
            else:
                freshness = f"{age / 3600:.1f}h old"
            scanner.append(
                {
                    "Asset": str(row.get("symbol", "")).replace("USDT", ""),
                    "Live price": short_price(row.get("price")),
                    "24H ref": "Unavailable" if row.get("reference_change_percent") is None else f"{safe_float(row.get('reference_change_percent')):+.2f}%",
                    "+15m forecast": short_price(row.get("forecast_price_15m")),
                    "Forecast move": "Unavailable" if row.get("forecast_move_percent_15m") is None else f"{safe_float(row.get('forecast_move_percent_15m')):+.3f}%",
                    "Direction": status_label(row.get("direction")),
                    "P(up)": "Unavailable" if row.get("probability_up") is None else f"{safe_float(row.get('probability_up')) * 100:.1f}%",
                    "Risk": status_label(row.get("risk_level")),
                    "Anomaly": "Flagged" if row.get("is_anomaly") else "Normal",
                    "Freshness": freshness,
                }
            )
        st.dataframe(pd.DataFrame(scanner), use_container_width=True, hide_index=True)
    else:
        st.caption("Market scanner will populate when the overview endpoint receives live records.")

    section("Technical indicators", "Latest engineered features from the live analytics layer.")
    indicator_specs = [
        ("RSI 14", selected.get("rsi_14"), 2),
        ("MACD", selected.get("macd"), 5),
        ("ATR %", selected.get("atr_pct"), 5),
        ("Volatility 20", selected.get("vol_20"), 5),
    ]
    cols = st.columns(4)
    for col, (label, value, digits) in zip(cols, indicator_specs):
        with col:
            display = "Unavailable" if value is None else f"{safe_float(value):.{digits}f}"
            metric_card(label, display, "Latest engineered feature")

    section(
        "Market advisor preview",
        "Recommendations are generated for all four supported assets even when your portfolio has no holdings.",
    )
    if is_authenticated():
        try:
            response = get_recommendations(get_token())
            if response.status_code == 200:
                recs = response.json().get("recommendations", [])
                if recs:
                    rec_cols = st.columns(4)
                    for col, rec in zip(rec_cols, recs[:4]):
                        with col:
                            context = "Held position" if rec.get("is_held") else "Market watch"
                            action = status_label(rec.get("recommendation"))
                            metric_card(
                                rec.get("symbol", "").replace("USDT", ""),
                                action,
                                f"{context} · {status_label(rec.get('confidence'))} confidence",
                                "accent" if action == "Positive Bias" else "danger" if action == "Negative Bias" else "neutral",
                            )
                else:
                    st.caption("Advisor is waiting for market analytics.")
        except Exception as exc:
            st.caption(f"Advisor preview unavailable: {exc}")
    else:
        login_cta()

    st.markdown(
        "<div class='rta-review-note'><b>Screen-recording statement:</b> The system ingests live market candles, computes analytics and runs an asset-specific GRU V4. "
        "The gold +15m point is the direct trained prediction. Later one-hour points are deliberately marked as scenarios, so the dashboard does not overclaim the current model.</div>",
        unsafe_allow_html=True,
    )

    if refresh_seconds > 0:
        time.sleep(refresh_seconds)
        st.rerun()

def render_markets():
    page_heading(
        "Markets",
        "Explore live analytics with 24-hour, 7-day and 30-day historical context.",
        "Authenticated",
    )
    rows, error = fetch_latest()
    if error:
        api_error("Unable to load the current market snapshot.", error)
        return
    render_asset_strip(rows)

    section("Asset explorer", "Inspect price history, live analytics and the current GRU V4 forecast.")
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        symbol = st.selectbox(
            "Asset",
            SYMBOLS,
            format_func=lambda s: f"{SYMBOL_NAMES[s]} · {s}",
        )
    with c2:
        period = st.selectbox(
            "History",
            ["1d", "7d", "30d"],
            index=2,
            format_func=lambda value: {"1d": "24 hours", "7d": "7 days", "30d": "30 days"}[value],
        )
    with c3:
        refresh = st.selectbox(
            "Refresh",
            [0, 5, 10, 30, 60],
            index=0,
            format_func=lambda x: "Manual" if x == 0 else f"Every {x}s",
        )

    selected = market_map(rows).get(symbol, {})
    risk = selected.get("risk") or {}
    anomaly = selected.get("anomaly") or {}
    prediction = selected.get("prediction") or {}

    try:
        history_payload = get_market_history(
            symbol,
            limit=1800,
            period=period,
            interval="auto",
        )
        history = history_dataframe(history_payload)
        stats = history_payload.get("stats") or {}
    except Exception as exc:
        history_payload = {}
        history = pd.DataFrame()
        stats = {}
        api_error("Price history could not be loaded.", exc)

    period_label = {"1d": "24H", "7d": "7D", "30d": "30D"}[period]

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card("Live price", short_price(selected.get("close")), f"Open {short_price(selected.get('open'))}")
    with k2:
        change = stats.get("change_percent")
        metric_card(
            f"{period_label} change",
            "Unavailable" if change is None else f"{safe_float(change):+.2f}%",
            "Historical reference + live stream",
            "success" if change is not None and safe_float(change) >= 0 else "danger" if change is not None else "neutral",
        )
    with k3:
        metric_card(
            "Market risk",
            status_label(risk.get("level")),
            f"{safe_float(risk.get('score')):.1f}/100",
        )
    with k4:
        forecast_value = status_label(prediction.get("direction")) if prediction.get("direction") else "Warming up"
        probability = prediction.get("probability_up")
        forecast_meta = (
            f"P(up) {safe_float(probability) * 100:.1f}% · GRU V4"
            if probability is not None
            else status_label(prediction.get("status") or "Unavailable")
        )
        metric_card("15m forecast", forecast_value, forecast_meta)

    chart_col, risk_col = st.columns([1.7, .9])
    with chart_col:
        price_chart(
            history,
            symbol,
            prediction=prediction,
            current_price=selected.get("close"),
            current_timestamp=selected.get("timestamp"),
            height=420,
        )
        st.caption(
            f"{period_label} historical reference with the current live stream. "
            "Experimental forecast markers are derived only from live GRU V4 outputs."
        )
    with risk_col:
        risk_gauge(risk.get("score"), risk.get("level"))
        signal_row(f"{period_label} high", short_price(stats.get("high")), "Observed range")
        signal_row(f"{period_label} low", short_price(stats.get("low")), "Observed range")

    section("Indicators", "Latest engineered features from the streaming analytics layer.")
    indicators = [
        ("RSI 14", selected.get("rsi_14")),
        ("MACD", selected.get("macd")),
        ("ATR %", selected.get("atr_pct")),
        ("Volatility 20", selected.get("vol_20")),
        ("Order flow imbalance", selected.get("order_flow_imbalance")),
        ("Taker buy ratio", selected.get("taker_buy_ratio")),
    ]
    cols = st.columns(3)
    for idx, (label, value) in enumerate(indicators):
        with cols[idx % 3]:
            st.metric(label, "Unavailable" if value is None else f"{safe_float(value):.5f}")

    with st.expander("Forecast interpretation"):
        if prediction.get("direction"):
            st.write(
                f"Experimental GRU V4 direction: **{status_label(prediction.get('direction'))}**"
            )
            if prediction.get("probability_up") is not None:
                st.write(
                    f"Probability up: **{safe_float(prediction.get('probability_up')) * 100:.2f}%**"
                )
            raw_return = prediction.get("predicted_log_return", prediction.get("value"))
            if raw_return is not None:
                st.write(
                    f"Predicted 15-minute log return: **{safe_float(raw_return) * 100:+.4f}%**"
                )
                try:
                    forecast_price = safe_float(selected.get("close")) * math.exp(safe_float(raw_return))
                    st.write(f"Derived 15-minute forecast price: **{short_price(forecast_price)}**")
                except Exception:
                    pass
            st.caption(
                "Each asset has its own 60 × 50 GRU V4 model. Forecasts are experimental and are not investment guarantees."
            )
        else:
            st.info(
                f"GRU V4 forecast is not ready for this record: "
                f"{status_label(prediction.get('status') or 'Unavailable')}."
            )
        st.caption(
            "Historical data provides context only. Historical GRU predictions are not fabricated; forecast markers appear only for actual live model outputs."
        )

    if refresh > 0:
        time.sleep(refresh)
        st.rerun()


def render_portfolio_overview(data: dict):
    holdings = data.get("holdings", [])
    summary = data.get("portfolio_summary") or data
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Current value", money(summary.get("total_current_value")), "Live valuation")
    with c2:
        metric_card("Cost basis", money(summary.get("total_cost_basis")), "Acquisition cost")
    with c3:
        pnl_value = safe_float(summary.get("total_unrealized_pnl"))
        metric_card("Unrealized P&L", money(pnl_value), pct(summary.get("total_pnl_percent")), "success" if pnl_value >= 0 else "danger")
    with c4:
        metric_card("Assets held", str(len(holdings)), "Supported positions")

    if not holdings:
        empty_state("No holdings yet", "Record your first BUY transaction in the Transactions tab.")
        return
    df = pd.DataFrame(holdings)
    section("Holdings", "Current positions and live valuation.")
    display_cols = [c for c in ["symbol", "quantity", "average_cost", "current_price", "current_value", "unrealized_pnl", "pnl_percent", "total_fees"] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
    left, right = st.columns(2)
    with left:
        alloc = df.copy()
        alloc["current_value"] = pd.to_numeric(alloc.get("current_value"), errors="coerce").fillna(0)
        alloc = alloc[alloc["current_value"] > 0]
        if not alloc.empty:
            fig = px.pie(alloc, names="symbol", values="current_value", hole=.64)
            fig.update_layout(height=340, paper_bgcolor="rgba(0,0,0,0)", font={"color": "#AEBBCB"}, margin=dict(l=8, r=8, t=20, b=8), showlegend=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        pnl = df.copy()
        pnl["unrealized_pnl"] = pd.to_numeric(pnl.get("unrealized_pnl"), errors="coerce").fillna(0)
        fig = px.bar(pnl, x="symbol", y="unrealized_pnl")
        fig.add_hline(y=0, line_width=1)
        fig.update_layout(height=340, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#AEBBCB"}, margin=dict(l=8, r=8, t=20, b=8), xaxis_title=None, yaxis_title="Unrealized P&L")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_transaction_desk():
    section("Transaction desk", "Record BUY and SELL transactions. Overselling remains blocked by the backend.")
    with st.form("transaction_desk"):
        a, b, c, d, e = st.columns([1.2, .8, 1, 1, .8])
        with a:
            symbol = st.selectbox("Asset", SYMBOLS)
        with b:
            side = st.selectbox("Side", ["BUY", "SELL"])
        with c:
            quantity = st.number_input("Quantity", min_value=0.00000001, value=0.001, format="%.8f")
        with d:
            price = st.number_input("Execution price", min_value=0.00000001, value=1.0, format="%.8f")
        with e:
            fees = st.number_input("Fees", min_value=0.0, value=0.0, format="%.8f")
        submitted = st.form_submit_button("Record transaction", use_container_width=True)
    if submitted:
        try:
            response = create_transaction(get_token(), symbol, side, quantity, price, fees)
            if response.status_code in (200, 201):
                st.success(f"{side} transaction recorded.")
                st.rerun()
            else:
                st.error(response_detail(response, "Transaction failed."))
        except Exception as exc:
            api_error("Unable to record the transaction.", exc)


def render_personalized_insights():
    try:
        response = get_personalized_analytics(get_token())
    except Exception as exc:
        api_error("Unable to load personalized analytics.", exc)
        return
    if response.status_code != 200:
        st.error(response_detail(response, "Personalized analytics request failed."))
        return
    data = response.json()
    summary = data.get("portfolio_summary") or {}
    a, b, c, d = st.columns(4)
    with a:
        metric_card("Risk tolerance", status_label(data.get("risk_tolerance")), "Personalization profile")
    with b:
        metric_card("Portfolio value", money(summary.get("total_current_value")), "Current market value")
    with c:
        metric_card("Unrealized P&L", money(summary.get("total_unrealized_pnl")), pct(summary.get("total_pnl_percent")))
    with d:
        metric_card("Assets analyzed", str(len(data.get("assets", []))), "Held assets")

    assets = data.get("assets", [])
    if not assets:
        empty_state("No personalized insights yet", "Add a supported asset to the portfolio first.")
        return
    section("Portfolio-aware intelligence", "Each held asset is interpreted with current market analytics.")
    for asset in assets:
        symbol = asset.get("symbol", "UNKNOWN")
        risk = asset.get("risk") or {}
        anomaly = asset.get("anomaly") or {}
        prediction = asset.get("prediction") or {}
        with st.expander(f"{symbol} · {SYMBOL_NAMES.get(symbol, symbol)}", expanded=symbol == "BTCUSDT"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Current value", money(asset.get("current_value")))
            with c2:
                st.metric("Unrealized P&L", money(asset.get("unrealized_pnl")))
            with c3:
                st.metric("Market risk", status_label(risk.get("level")), f"{safe_float(risk.get('score')):.1f}/100")
            with c4:
                st.metric("Anomaly", "Flagged" if anomaly.get("is_anomaly") else "Normal")
            if symbol == "BTCUSDT":
                st.caption(f"Experimental GRU: {status_label(prediction.get('direction'))} · {prediction.get('source', 'Unavailable')}")


def render_portfolio():
    page_heading("Portfolio", "Track positions, transactions and personalized analytics.", get_username() or "Account")
    try:
        response = get_portfolio(get_token())
    except Exception as exc:
        api_error("Unable to load the portfolio.", exc)
        return
    if response.status_code != 200:
        st.error(response_detail(response, "Portfolio request failed."))
        return
    data = response.json()
    overview, transactions, insights = st.tabs(["Overview", "Transactions", "Insights"])
    with overview:
        render_portfolio_overview(data)
    with transactions:
        render_transaction_desk()
    with insights:
        render_personalized_insights()


def render_recommendations():
    try:
        response = get_recommendations(get_token())
    except Exception as exc:
        api_error("Unable to load recommendations.", exc)
        return
    if response.status_code != 200:
        st.error(response_detail(response, "Recommendations request failed."))
        return

    data = response.json()
    st.caption(
        f"Active risk tolerance · **{status_label(data.get('risk_tolerance'))}** · "
        "Signals cover all four supported assets whether held or not."
    )
    recommendations = data.get("recommendations", [])
    if not recommendations:
        empty_state("No recommendation signals", "Wait for live market analytics and valid model outputs.")
        return

    summary_rows = []
    for rec in recommendations:
        summary_rows.append(
            {
                "Asset": rec.get("symbol", "").replace("USDT", ""),
                "Context": "Held position" if rec.get("is_held") else "Market watch",
                "Signal": status_label(rec.get("recommendation")),
                "Confidence": status_label(rec.get("confidence")),
                "Risk tolerance": status_label(rec.get("risk_tolerance")),
            }
        )
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    for rec in recommendations:
        symbol = rec.get("symbol", "UNKNOWN")
        action = status_label(rec.get("recommendation"))
        confidence = status_label(rec.get("confidence"))
        context = "Held position" if rec.get("is_held") else "Market watch · no investment required"
        st.markdown("<div class='rta-panel'>", unsafe_allow_html=True)
        head, conf = st.columns([3, 1])
        with head:
            st.markdown(f"**{symbol} · {action}**")
            st.caption(context)
            for reason in rec.get("reasons", []):
                st.write(f"• {reason}")
        with conf:
            metric_card("Confidence", confidence, f"Risk · {status_label(rec.get('risk_tolerance'))}")
        for warning in rec.get("warnings", []):
            st.warning(warning)
        st.markdown("</div>", unsafe_allow_html=True)

def render_risk_profile():
    try:
        response = get_risk_profile(get_token())
    except Exception as exc:
        api_error("Unable to load the risk profile.", exc)
        return
    if response.status_code != 200:
        st.error(response_detail(response, "Risk profile request failed."))
        return
    current = str(response.json().get("risk_tolerance", "medium")).lower()
    choices = ["low", "medium", "high"]
    selected = st.radio("Risk tolerance", choices, index=choices.index(current), horizontal=True, format_func=str.title)
    descriptions = {
        "low": "More cautious personalization when market risk or anomalies are elevated.",
        "medium": "Balanced personalization between market opportunity and current risk conditions.",
        "high": "Allows higher market-risk tolerance in the recommendation context.",
    }
    st.info(descriptions[selected])
    if st.button("Save risk profile", type="primary"):
        try:
            update = update_risk_profile(get_token(), selected)
            if update.status_code == 200:
                st.success(f"Risk tolerance updated to {selected.title()}.")
            else:
                st.error(response_detail(update, "Risk profile update failed."))
        except Exception as exc:
            api_error("Unable to update the risk profile.", exc)


def render_advisor():
    page_heading("Advisor", "Market-wide decision support across BTC, ETH, BNB and SOL, with portfolio context added when you hold an asset.", "Market + personalized")
    recommendations, profile = st.tabs(["Recommendations", "Risk profile"])
    with recommendations:
        render_recommendations()
    with profile:
        render_risk_profile()


def render_alerts():
    page_heading("Alerts", "Monitor portfolio-relevant anomalies, risk conditions and supported signal events.", "Personalized")
    top1, top2, top3 = st.columns([1.1, 1, 1])
    with top1:
        if st.button("Generate latest alerts", type="primary", use_container_width=True):
            try:
                response = generate_alerts(get_token())
                if response.status_code == 200:
                    count = response.json().get("count", 0)
                    st.success(f"Generated {count} new alert(s)." if count else "No new alerts were generated.")
                else:
                    st.error(response_detail(response, "Alert generation failed."))
            except Exception as exc:
                api_error("Unable to generate alerts.", exc)
    with top2:
        unread_only = st.checkbox("Unread only", value=False)
    with top3:
        limit = st.selectbox("Max alerts", [10, 25, 50, 100], index=2)

    try:
        response = get_alerts(get_token(), unread_only=unread_only, limit=limit)
    except Exception as exc:
        api_error("Unable to load alerts.", exc)
        return
    if response.status_code != 200:
        st.error(response_detail(response, "Alerts request failed."))
        return
    payload = response.json()
    alerts = payload.get("data", payload.get("alerts", payload if isinstance(payload, list) else []))
    if not alerts:
        empty_state("No alerts", "No alerts match the current filter.")
        return
    unread_count = sum(1 for a in alerts if not a.get("read", False))
    section(f"{len(alerts)} alerts · {unread_count} unread", "Newest alerts are shown first.")
    for alert in alerts:
        severity = status_label(alert.get("severity"))
        title = f"{alert.get('symbol', 'MARKET')} · {status_label(alert.get('type'))} · {severity}"
        with st.expander(title, expanded=not alert.get("read", False)):
            st.write(alert.get("message", "No message."))
            st.caption(f"Created · {parse_time(alert.get('created_at'))}")
            if not alert.get("read", False) and alert.get("id"):
                if st.button("Mark as read", key=f"read_{alert['id']}"):
                    result = mark_alert_read(get_token(), alert["id"])
                    if result.status_code == 200:
                        st.rerun()
                    else:
                        st.error(response_detail(result, "Could not update alert."))


def render_about():
    st.markdown(
        """
        <div class="rta-about-hero">
          <div class="rta-about-kicker">About RTA</div>
          <div class="rta-about-title">Real-time crypto analytics with a personalized investor layer.</div>
          <div class="rta-about-copy">RTA combines streaming market data, engineered analytics, risk scoring, anomaly detection, experimental forecasting, portfolio tracking and personalized recommendations. Technical details are kept here so the main product experience stays focused on decisions and market context.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    product_tab, architecture_tab, models_tab = st.tabs(["Product", "Architecture", "Model evaluation"])

    with product_tab:
        section("What the product does", "One interface for market intelligence and investor-specific context.")
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Market intelligence", "4 assets", "BTC, ETH, BNB and SOL")
        with c2:
            metric_card("Analytics", "Risk + anomaly", "Independent analytical layers")
        with c3:
            metric_card("Personalization", "Portfolio-aware", "Risk profile, recommendations and alerts")
        st.markdown("<div class='rta-note'>The public dashboard shows market intelligence without requiring an account. Authentication is only required for user-specific portfolio, advisor and alert features.</div>", unsafe_allow_html=True)

    with architecture_tab:
        section("System architecture", "Streaming ingestion, analytics, persistence, API and frontend are separated by responsibility.")
        st.markdown(
            """
            <div class="rta-flow">
              <div class="rta-flow-node">BINANCE</div><div class="rta-flow-arrow">→</div>
              <div class="rta-flow-node">KAFKA</div><div class="rta-flow-arrow">→</div>
              <div class="rta-flow-node">SPARK</div><div class="rta-flow-arrow">→</div>
              <div class="rta-flow-node">ANALYTICS</div>
            </div>
            <div style="height:.42rem"></div>
            <div class="rta-flow">
              <div class="rta-flow-node">MONGODB</div><div class="rta-flow-arrow">→</div>
              <div class="rta-flow-node">FASTAPI</div><div class="rta-flow-arrow">→</div>
              <div class="rta-flow-node">STREAMLIT</div><div class="rta-flow-arrow">→</div>
              <div class="rta-flow-node">USER</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        section("Analytics layers", "Global market analytics remain shared. Personalization is applied after portfolio and risk-profile context are available.")
        a, b = st.columns(2)
        with a:
            metric_card("Risk engine", RISK_ENGINE["name"], RISK_ENGINE["levels"])
            st.write("")
            for name, weight in RISK_ENGINE["weights"].items():
                st.progress(weight, text=f"{name} · {weight:.0%}")
        with b:
            metric_card("Anomaly engine", ANOMALY_ENGINE["name"], f"{ANOMALY_ENGINE['feature_count']} features · {ANOMALY_ENGINE['n_estimators']} estimators")
            st.write("")
            st.caption(f"Contamination: {ANOMALY_ENGINE['contamination']:.0%}")
            st.caption(f"Random state: {ANOMALY_ENGINE['random_state']}")
            st.markdown("<div class='rta-note'>An anomaly means unusual feature behaviour. It is not automatically a negative event or a trading signal.</div>", unsafe_allow_html=True)

    with models_tab:
        section("GRU V4 live models", "Four independent asset-specific models now power the live prediction layer.")
        c1, c2, c3, c4 = st.columns(4)
        for col, symbol in zip((c1, c2, c3, c4), SYMBOLS):
            with col:
                metric_card(symbol.replace("USDT", ""), "GRU V4", "60 × 50 input · 15m horizon", "accent")

        st.markdown(
            "<div class='rta-note'>Each asset has its own trained GRU V4. The models are experimental. "
            "The test results are shown transparently and should not be interpreted as guaranteed predictive accuracy.</div>",
            unsafe_allow_html=True,
        )

        try:
            comparison_payload = get_model_comparison()
        except Exception:
            comparison_payload = load_comparison_results()

        rows = comparison_rows(comparison_payload)
        gru_rows = [row for row in rows if row.get("Model") == "GRU V4"]
        if gru_rows:
            section("Final GRU V4 test results", "Held-out test metrics from the completed four-model training run.")
            gru_display = []
            for row in gru_rows:
                item = dict(row)
                if item.get("Direction accuracy") is not None:
                    item["Direction accuracy"] = safe_float(item["Direction accuracy"]) * 100.0
                gru_display.append(item)
            gru_df = pd.DataFrame(gru_display)
            st.dataframe(
                gru_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "R²": st.column_config.NumberColumn(format="%.5f"),
                    "RMSE": st.column_config.NumberColumn(format="%.6f"),
                    "Direction accuracy": st.column_config.NumberColumn(format="%.2f%%"),
                    "AUC": st.column_config.NumberColumn(format="%.4f"),
                    "Correlation": st.column_config.NumberColumn(format="%.4f"),
                },
            )

        if rows:
            section("Comparative analysis", "GRU V4 compared with XGBoost and the Chronos-2 benchmark across all supported assets.")
            display_rows = []
            for row in rows:
                item = dict(row)
                if item.get("Direction accuracy") is not None:
                    item["Direction accuracy"] = safe_float(item["Direction accuracy"]) * 100.0
                display_rows.append(item)
            comparison_df = pd.DataFrame(display_rows)
            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "R²": st.column_config.NumberColumn(format="%.5f"),
                    "RMSE": st.column_config.NumberColumn(format="%.6f"),
                    "Direction accuracy": st.column_config.NumberColumn(format="%.2f%%"),
                    "AUC": st.column_config.NumberColumn(format="%.4f"),
                    "Correlation": st.column_config.NumberColumn(format="%.4f"),
                },
            )

        st.caption(
            "Near-zero or negative R² is possible for noisy 15-minute cryptocurrency returns. "
            "The review therefore reports regression error, direction accuracy, AUC and correlation together rather than presenting one metric as proof of accuracy."
        )

        with st.expander("GRU V4 architecture"):
            for index, layer in enumerate(ARCHITECTURE, start=1):
                st.write(f"{index}. {layer}")


page = render_header()

if page == "Dashboard":
    render_dashboard()
elif page == "About":
    render_about()
elif not is_authenticated():
    st.session_state["active_page"] = "Dashboard"
    st.rerun()
elif page == "Markets":
    render_markets()
elif page == "Portfolio":
    render_portfolio()
elif page == "Advisor":
    render_advisor()
elif page == "Alerts":
    render_alerts()
else:
    st.session_state["active_page"] = "Dashboard"
    st.rerun()
