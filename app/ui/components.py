from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


SYMBOL_NAMES = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "BNBUSDT": "BNB",
    "SOLUSDT": "Solana",
}

SYMBOL_TICKERS = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "BNBUSDT": "BNB",
    "SOLUSDT": "SOL",
}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def money(value: Any, digits: int = 2) -> str:
    return f"${safe_float(value):,.{digits}f}"


def pct(value: Any, digits: int = 2) -> str:
    return f"{safe_float(value):,.{digits}f}%"


def short_price(value: Any) -> str:
    if value is None:
        return "Unavailable"
    number = safe_float(value)
    if number >= 1000:
        return f"${number:,.2f}"
    if number >= 1:
        return f"${number:,.4f}"
    return f"${number:,.6f}"


def status_label(value: str | None) -> str:
    if not value:
        return "Unavailable"
    return str(value).replace("_", " ").title()


def parse_time(value: Any) -> str:
    if value is None:
        return "Unavailable"
    try:
        if isinstance(value, (int, float)):
            raw = float(value)
            if raw > 1e15:
                raw /= 1_000_000
            elif raw > 1e12:
                raw /= 1000
            dt = datetime.fromtimestamp(raw, tz=timezone.utc)
            return dt.strftime("%d %b %Y · %H:%M UTC")
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    except Exception:
        return str(value)


def normalize_record(record: dict | None) -> dict:
    if not isinstance(record, dict):
        return {}
    normalized = dict(record)
    market = record.get("market") or {}
    features = record.get("features") or {}
    for key, value in market.items():
        normalized.setdefault(key, value)
    for key, value in features.items():
        normalized.setdefault(key, value)
    return normalized


def history_dataframe(payload: dict) -> pd.DataFrame:
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    if not rows:
        return pd.DataFrame()

    normalized_rows = []
    for row in rows:
        item = normalize_record(row)
        item["source_type"] = row.get("source_type", item.get("source_type", "live"))
        if row.get("forecast_price") is not None:
            item["forecast_price"] = row.get("forecast_price")
        if row.get("forecast_timestamp") is not None:
            item["forecast_timestamp"] = row.get("forecast_timestamp")
        normalized_rows.append(item)

    df = pd.DataFrame(normalized_rows)
    if "timestamp" in df.columns:
        ts = pd.to_numeric(df["timestamp"], errors="coerce")
        if ts.notna().any():
            median = ts.dropna().median()
            divisor = 1_000_000 if median > 1e14 else 1000 if median > 1e11 else 1
            df["timestamp_dt"] = pd.to_datetime(ts / divisor, unit="s", utc=True, errors="coerce")
            missing = df["timestamp_dt"].isna()
            if missing.any():
                df.loc[missing, "timestamp_dt"] = pd.to_datetime(
                    df.loc[missing, "timestamp"], utc=True, errors="coerce"
                )
        else:
            df["timestamp_dt"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    else:
        df["timestamp_dt"] = pd.RangeIndex(len(df))

    if "forecast_timestamp" in df.columns:
        df["forecast_timestamp_dt"] = pd.to_datetime(
            df["forecast_timestamp"], utc=True, errors="coerce"
        )

    return df.sort_values("timestamp_dt")


def section(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="rta-section-heading">
          <div class="rta-section-title">{escape(title)}</div>
          <div class="rta-section-subtitle">{escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_heading(title: str, subtitle: str = "", badge: str | None = None):
    badge_html = f'<span class="rta-badge rta-badge-live">{escape(badge)}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="rta-page-heading">
          <div>
            <div class="rta-page-title">{escape(title)}</div>
            <div class="rta-page-subtitle">{escape(subtitle)}</div>
          </div>
          <div>{badge_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, meta: str = "", tone: str = "neutral"):
    tone_class = f" rta-card-{tone}" if tone in {"success", "warning", "danger", "accent"} else ""
    st.markdown(
        f"""
        <div class="rta-metric-card{tone_class}">
          <div class="rta-metric-label">{escape(str(label))}</div>
          <div class="rta-metric-value">{escape(str(value))}</div>
          <div class="rta-metric-meta">{escape(str(meta))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def market_card(symbol: str, record: dict):
    risk = record.get("risk") or {}
    anomaly = record.get("anomaly") or {}
    risk_level = status_label(risk.get("level"))
    risk_class = "low" if risk_level.lower() == "low" else "high" if risk_level.lower() == "high" else "medium"
    anomaly_html = '<span class="rta-dot rta-dot-danger"></span> Flagged' if anomaly.get("is_anomaly") else '<span class="rta-dot rta-dot-success"></span> Normal'
    st.markdown(
        f"""
        <div class="rta-market-card">
          <div class="rta-market-card-top">
            <div>
              <div class="rta-symbol">{escape(SYMBOL_TICKERS.get(symbol, symbol))}</div>
              <div class="rta-asset-name">{escape(SYMBOL_NAMES.get(symbol, symbol))}</div>
            </div>
            <div class="rta-risk-chip rta-risk-{risk_class}">{escape(risk_level)}</div>
          </div>
          <div class="rta-market-price">{escape(short_price(record.get('close')))}</div>
          <div class="rta-market-footer"><span>Risk {safe_float(risk.get('score')):.1f}</span><span>{anomaly_html}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def signal_row(label: str, value: str, note: str = ""):
    st.markdown(
        f"""
        <div class="rta-signal-row">
          <div>
            <div class="rta-signal-label">{escape(label)}</div>
            <div class="rta-signal-note">{escape(note)}</div>
          </div>
          <div class="rta-signal-value">{escape(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def login_cta():
    st.markdown(
        """
        <div class="rta-login-cta">
          <div>
            <div class="rta-login-cta-title">Unlock your investor workspace</div>
            <div class="rta-login-cta-copy">Sign in to access portfolio tracking, personalized insights, recommendations, risk profile and alerts.</div>
          </div>
          <div class="rta-login-cta-tag">PERSONALIZED</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(title: str, copy: str):
    st.markdown(
        f"""
        <div class="rta-empty-state">
          <div class="rta-empty-title">{escape(title)}</div>
          <div class="rta-empty-copy">{escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def price_chart(
    df: pd.DataFrame,
    symbol: str,
    prediction: dict | None = None,
    current_price: Any = None,
    current_timestamp: Any = None,
    outlook: dict | None = None,
    height: int = 390,
):
    if df.empty or "close" not in df.columns:
        empty_state(
            "Price history unavailable",
            "Prepare the dashboard history asset, then start the live streaming pipeline.",
        )
        return

    fig = go.Figure()
    has_source = "source_type" in df.columns

    if has_source:
        historical = df[df["source_type"].fillna("historical") == "historical"].copy()
        live = df[df["source_type"].fillna("live") == "live"].copy()
    else:
        historical = df.copy()
        live = pd.DataFrame()

    if not historical.empty:
        historical["close"] = pd.to_numeric(historical["close"], errors="coerce")
        fig.add_trace(
            go.Scatter(
                x=historical["timestamp_dt"],
                y=historical["close"],
                mode="lines",
                name="Historical",
                line={"width": 2.1, "color": "#6E8FC8"},
                hovertemplate="%{x}<br>Historical price: $%{y:,.4f}<extra></extra>",
            )
        )

    if not live.empty:
        live["close"] = pd.to_numeric(live["close"], errors="coerce")
        fig.add_trace(
            go.Scatter(
                x=live["timestamp_dt"],
                y=live["close"],
                mode="lines+markers" if len(live) < 30 else "lines",
                name="Live",
                line={"width": 2.7, "color": "#5DD6C7"},
                marker={"size": 5},
                hovertemplate="%{x}<br>Live price: $%{y:,.4f}<extra></extra>",
            )
        )

        if "forecast_price" in live.columns and "forecast_timestamp_dt" in live.columns:
            forecast = live.dropna(subset=["forecast_price", "forecast_timestamp_dt"]).copy()
            if not forecast.empty:
                forecast["forecast_price"] = pd.to_numeric(
                    forecast["forecast_price"], errors="coerce"
                )
                fig.add_trace(
                    go.Scatter(
                        x=forecast["forecast_timestamp_dt"],
                        y=forecast["forecast_price"],
                        mode="markers",
                        name="GRU V4 forecasts",
                        marker={"size": 6, "symbol": "diamond", "color": "#E8B86D"},
                        hovertemplate=(
                            "%{x}<br>Experimental 15m forecast: $%{y:,.4f}"
                            "<extra></extra>"
                        ),
                    )
                )

    # Always draw the newest 15-minute experimental forecast when possible.
    prediction = prediction or {}
    raw_return = prediction.get("predicted_log_return", prediction.get("value"))
    try:
        latest_close = float(current_price)
        predicted_return = float(raw_return)
        latest_ts = pd.to_datetime(current_timestamp, utc=True, errors="coerce")
        if pd.notna(latest_ts):
            import math

            forecast_price = latest_close * math.exp(predicted_return)
            forecast_ts = latest_ts + pd.Timedelta(minutes=15)
            fig.add_trace(
                go.Scatter(
                    x=[latest_ts, forecast_ts],
                    y=[latest_close, forecast_price],
                    mode="lines+markers",
                    name="Current 15m forecast",
                    line={"width": 2, "dash": "dot", "color": "#E8B86D"},
                    marker={"size": [5, 9], "symbol": ["circle", "diamond"]},
                    hovertemplate=(
                        "%{x}<br>Price / experimental forecast: $%{y:,.4f}"
                        "<extra></extra>"
                    ),
                )
            )
    except (TypeError, ValueError, OverflowError):
        pass



    # Review-only horizon extension. The +15m point remains the only direct model
    # forecast. Later points are explicitly styled and labelled as scenario output.
    if outlook and isinstance(outlook.get("points"), list):
        scenario_points = [
            point for point in outlook.get("points", [])
            if point.get("kind") in ("DIRECT_MODEL", "SCENARIO_EXTENSION")
        ]
        if len(scenario_points) >= 2:
            scenario_df = pd.DataFrame(scenario_points)
            scenario_df["timestamp_dt"] = pd.to_datetime(
                scenario_df["timestamp"], utc=True, errors="coerce"
            )
            scenario_df["price"] = pd.to_numeric(
                scenario_df["price"], errors="coerce"
            )
            scenario_df = scenario_df.dropna(subset=["timestamp_dt", "price"])
            if len(scenario_df) >= 2:
                fig.add_trace(
                    go.Scatter(
                        x=scenario_df["timestamp_dt"],
                        y=scenario_df["price"],
                        mode="lines+markers",
                        name="1h scenario extension",
                        line={"width": 1.8, "dash": "dash", "color": "#9AA7FF"},
                        marker={"size": 7, "symbol": "circle-open", "color": "#9AA7FF"},
                        customdata=scenario_df[["label", "kind"]].to_numpy(),
                        hovertemplate=(
                            "%{x}<br>%{customdata[0]}<br>Price: $%{y:,.4f}"
                            "<br>%{customdata[1]}<extra></extra>"
                        ),
                    )
                )

    fig.update_layout(
        height=height,
        margin=dict(l=4, r=8, t=12, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#8DA0B7", "size": 11},
        hovermode="x unified",
        xaxis={
            "gridcolor": "rgba(148,163,184,.065)",
            "title": None,
            "showline": False,
        },
        yaxis={
            "gridcolor": "rgba(148,163,184,.065)",
            "title": None,
            "side": "right",
            "tickprefix": "$",
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 10},
        },
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})




def prediction_timeline(outlook: dict | None, height: int = 285):
    """Render the direct +15m model forecast and clearly separate later scenarios."""
    if not outlook or not outlook.get("points"):
        empty_state(
            "Forecast horizon unavailable",
            "Wait for a valid GRU V4 output from the live streaming pipeline.",
        )
        return

    frame = pd.DataFrame(outlook.get("points", []))
    if frame.empty or "price" not in frame.columns:
        empty_state("Forecast horizon unavailable", "No valid forecast points are present.")
        return

    frame["timestamp_dt"] = pd.to_datetime(frame.get("timestamp"), utc=True, errors="coerce")
    frame["price"] = pd.to_numeric(frame.get("price"), errors="coerce")
    frame = frame.dropna(subset=["timestamp_dt", "price"])
    if frame.empty:
        empty_state("Forecast horizon unavailable", "Forecast timestamps or prices are invalid.")
        return

    current = frame[frame["kind"] == "CURRENT"]
    direct = frame[frame["kind"] == "DIRECT_MODEL"]
    scenario = frame[frame["kind"] == "SCENARIO_EXTENSION"]

    fig = go.Figure()
    if not current.empty:
        fig.add_trace(
            go.Scatter(
                x=current["timestamp_dt"],
                y=current["price"],
                mode="markers+text",
                name="Current",
                marker={"size": 10, "color": "#5DD6C7"},
                text=["Now"],
                textposition="top center",
                hovertemplate="Current<br>%{x}<br>$%{y:,.4f}<extra></extra>",
            )
        )
    if not direct.empty:
        fig.add_trace(
            go.Scatter(
                x=direct["timestamp_dt"],
                y=direct["price"],
                mode="markers+text",
                name="Direct GRU V4",
                marker={"size": 13, "symbol": "diamond", "color": "#E8B86D"},
                text=direct["label"],
                textposition="top center",
                hovertemplate="Direct model forecast<br>%{x}<br>$%{y:,.4f}<extra></extra>",
            )
        )
    # Connect current to direct model output.
    if not current.empty and not direct.empty:
        pair = pd.concat([current, direct]).sort_values("timestamp_dt")
        fig.add_trace(
            go.Scatter(
                x=pair["timestamp_dt"],
                y=pair["price"],
                mode="lines",
                name="Model horizon",
                line={"width": 2.4, "dash": "dot", "color": "#E8B86D"},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    if not scenario.empty:
        chain = pd.concat([direct, scenario]).sort_values("timestamp_dt") if not direct.empty else scenario
        fig.add_trace(
            go.Scatter(
                x=chain["timestamp_dt"],
                y=chain["price"],
                mode="lines+markers+text",
                name="Scenario extension",
                line={"width": 2, "dash": "dash", "color": "#9AA7FF"},
                marker={"size": 7, "symbol": "circle-open", "color": "#9AA7FF"},
                text=["" if kind == "DIRECT_MODEL" else label for kind, label in zip(chain["kind"], chain["label"])],
                textposition="bottom center",
                hovertemplate="Scenario visualization<br>%{x}<br>$%{y:,.4f}<extra></extra>",
            )
        )

    fig.update_layout(
        height=height,
        margin=dict(l=4, r=8, t=18, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#8DA0B7", "size": 11},
        hovermode="x unified",
        xaxis={"gridcolor": "rgba(148,163,184,.065)", "title": None},
        yaxis={"gridcolor": "rgba(148,163,184,.065)", "title": None, "side": "right", "tickprefix": "$"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0, "font": {"size": 10}},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def risk_gauge(score: Any, level: str | None, height: int = 230):
    value = max(0.0, min(100.0, safe_float(score)))
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "/100", "font": {"size": 25, "color": "#F5F8FC"}},
            title={"text": f"Market risk · {status_label(level)}", "font": {"size": 12, "color": "#91A3B8"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#52657A"},
                "bar": {"thickness": 0.22, "color": "#5DD6C7"},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 33.33], "color": "rgba(72,199,142,.11)"},
                    {"range": [33.33, 66.67], "color": "rgba(236,188,83,.10)"},
                    {"range": [66.67, 100], "color": "rgba(238,101,124,.10)"},
                ],
            },
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=14, r=14, t=34, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#AEBBCB"},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def window_change(df: pd.DataFrame) -> float | None:
    if df.empty or "close" not in df.columns:
        return None
    values = pd.to_numeric(df["close"], errors="coerce").dropna()
    if len(values) < 2 or values.iloc[0] == 0:
        return None
    return ((values.iloc[-1] / values.iloc[0]) - 1.0) * 100.0


def api_error(title: str, exc: Exception | str):
    st.error(title)
    with st.expander("Technical details"):
        st.code(str(exc), language="text")
