"""Standalone RTA final model review page.

Run from the runtime project root:
    streamlit run app/model_review.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.model_comparison import comparison_rows, load_comparison_results
    from app.model_info import ARCHITECTURE
    from app.ui.components import metric_card, page_heading, section, safe_float
    from app.ui.theme import inject_theme
except ModuleNotFoundError:
    from model_comparison import comparison_rows, load_comparison_results
    from model_info import ARCHITECTURE
    from ui.components import metric_card, page_heading, section, safe_float
    from ui.theme import inject_theme

st.set_page_config(
    page_title="RTA | Final Model Evaluation",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_theme()
page_heading(
    "Final model evaluation",
    "Four asset-specific GRU V4 models and the completed comparative analysis.",
    "Experimental",
)

payload = load_comparison_results()
rows = comparison_rows(payload)
gru = {row["Asset"]: row for row in rows if row["Model"] == "GRU V4"}

section("GRU V4 deployment", "One independent 60 × 50 GRU model per supported cryptocurrency.")
cols = st.columns(4)
for col, symbol in zip(cols, ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]):
    row = gru.get(symbol, {})
    with col:
        acc = row.get("Direction accuracy")
        auc = row.get("AUC")
        metric_card(
            symbol.replace("USDT", ""),
            f"{safe_float(acc) * 100:.2f}% dir.",
            f"AUC {safe_float(auc):.4f}",
            "accent",
        )

if rows:
    section("Comparative analysis", "GRU V4, XGBoost and Chronos-2 on BTC, ETH, BNB and SOL.")
    display = []
    for row in rows:
        item = dict(row)
        if item.get("Direction accuracy") is not None:
            item["Direction accuracy"] = safe_float(item["Direction accuracy"]) * 100.0
        display.append(item)
    st.dataframe(
        pd.DataFrame(display),
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

st.markdown(
    "<div class='rta-note'>The final results do not support a high-accuracy claim. "
    "RTA reports regression and directional metrics transparently and uses the models as an experimental forecasting layer inside a broader real-time analytics system.</div>",
    unsafe_allow_html=True,
)

section("GRU V4 architecture", "The same model family is trained separately for each asset.")
for idx, layer in enumerate(ARCHITECTURE, 1):
    st.markdown(f"<div class='rta-panel'><b>{idx:02d}</b>&nbsp;&nbsp;{layer}</div>", unsafe_allow_html=True)
