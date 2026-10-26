# analytics/risk/risk_engine.py

"""
RTA Risk Analytics Engine
==========================

Deterministic market-risk scoring layer for the RTA pipeline.

The engine uses already-engineered market features and produces:

    risk.score  -> 0.0 to 100.0
    risk.level  -> LOW / MEDIUM / HIGH
    risk.source -> RISK_ENGINE_V1

This is NOT a trading strategy and does not execute trades.

Risk components:
    1. Volatility
    2. ATR
    3. Price range
    4. Volume abnormality
    5. Order-flow imbalance

The score is intentionally transparent so that the dashboard and
project review can explain why risk changed.
"""

from __future__ import annotations

import math
from typing import Any


# ============================================================================
# Configuration
# ============================================================================

RISK_SOURCE = "RISK_ENGINE_V1"

LOW_THRESHOLD = 33.33
HIGH_THRESHOLD = 66.67


# ============================================================================
# Feature weights
# ============================================================================

# The weights sum to 1.0.
#
# Volatility and ATR receive the largest contribution because they are
# direct measures of recent market movement.
#
# Range captures short-term price expansion.
#
# Volume and order-flow contribute additional market-stress information.

WEIGHTS = {
    "volatility": 0.30,
    "atr": 0.25,
    "range": 0.15,
    "volume": 0.15,
    "order_flow": 0.15,
}


# ============================================================================
# Utility
# ============================================================================

def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Convert a value into a finite float.

    Invalid / missing values return the supplied default.
    """

    try:

        result = float(value)

    except (
        TypeError,
        ValueError,
    ):

        return default

    if not math.isfinite(result):

        return default

    return result


def _clip(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    """
    Clamp a value into a fixed range.
    """

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


# ============================================================================
# Component scoring
# ============================================================================

def score_volatility(
    vol_20: Any,
    vol_60: Any,
) -> float:
    """
    Score realized volatility.

    The existing feature values are decimal return volatility values.

    Reference points:

        <= 0.002  -> very low
        0.010     -> moderate
        >= 0.030  -> very high

    The score is based primarily on vol_20, with vol_60 providing
    longer-window context.
    """

    short_vol = abs(
        _safe_float(vol_20)
    )

    long_vol = abs(
        _safe_float(vol_60)
    )

    short_score = _clip(
        (
            short_vol
            / 0.030
        )
        * 100.0
    )

    long_score = _clip(
        (
            long_vol
            / 0.030
        )
        * 100.0
    )

    score = (
        0.65 * short_score
        + 0.35 * long_score
    )

    return _clip(score)


def score_atr(
    atr_pct: Any,
) -> float:
    """
    Score ATR as a percentage of price.

    Reference points:

        <= 0.20% -> low
        1.00%    -> moderate
        >= 3.00% -> very high
    """

    value = abs(
        _safe_float(atr_pct)
    )

    score = (
        value
        / 0.03
    ) * 100.0

    return _clip(score)


def score_range(
    range_pct: Any,
) -> float:
    """
    Score current candle range as a percentage.

    Reference points:

        <= 0.20% -> low
        1.00%    -> moderate
        >= 3.00% -> very high
    """

    value = abs(
        _safe_float(range_pct)
    )

    score = (
        value
        / 0.03
    ) * 100.0

    return _clip(score)


def score_volume(
    volume_z_20: Any,
) -> float:
    """
    Score unusual volume using the 20-period volume z-score.

    A z-score close to zero represents normal volume.

    Larger absolute deviations indicate abnormal market activity.

    Reference points:

        <= 0.5 sigma -> low
        2.0 sigma    -> moderate/high
        >= 4.0 sigma -> very high
    """

    value = abs(
        _safe_float(volume_z_20)
    )

    score = (
        value
        / 4.0
    ) * 100.0

    return _clip(score)


def score_order_flow(
    order_flow_imbalance: Any,
) -> float:
    """
    Score order-flow imbalance.

    The feature is expected to be approximately centered around zero.

    Values near zero indicate balanced flow.

    Larger absolute imbalance indicates stronger directional pressure,
    which is treated as increased market risk rather than as a trading
    signal.
    """

    value = abs(
        _safe_float(
            order_flow_imbalance
        )
    )

    # The imbalance is normalized against a reference magnitude of 1.
    score = value * 100.0

    return _clip(score)


# ============================================================================
# Risk level
# ============================================================================

def risk_level(
    score: float,
) -> str:
    """
    Convert a 0–100 risk score into a categorical level.
    """

    score = _clip(
        score
    )

    if score < LOW_THRESHOLD:

        return "LOW"

    if score < HIGH_THRESHOLD:

        return "MEDIUM"

    return "HIGH"


# ============================================================================
# Main risk calculation
# ============================================================================

def calculate_risk(
    features: dict[str, Any],
) -> dict:
    """
    Calculate market risk from engineered features.

    Required features:

        vol_20
        vol_60
        atr_pct
        range_pct
        volume_z_20
        order_flow_imbalance

    Returns:

        {
            "score": float,
            "level": str,
            "source": "RISK_ENGINE_V1",
            "components": {
                ...
            }
        }
    """

    volatility_score = score_volatility(
        features.get("vol_20"),
        features.get("vol_60"),
    )

    atr_score = score_atr(
        features.get("atr_pct")
    )

    range_score = score_range(
        features.get("range_pct")
    )

    volume_score = score_volume(
        features.get("volume_z_20")
    )

    order_flow_score = score_order_flow(
        features.get("order_flow_imbalance")
    )

    # ------------------------------------------------------------------------
    # Weighted total
    # ------------------------------------------------------------------------

    total_score = (
        volatility_score
        * WEIGHTS["volatility"]
        + atr_score
        * WEIGHTS["atr"]
        + range_score
        * WEIGHTS["range"]
        + volume_score
        * WEIGHTS["volume"]
        + order_flow_score
        * WEIGHTS["order_flow"]
    )

    total_score = _clip(
        total_score
    )

    level = risk_level(
        total_score
    )

    result = {
        "score": round(
            total_score,
            4,
        ),

        "level": level,

        "source": RISK_SOURCE,

        "components": {
            "volatility": round(
                volatility_score,
                4,
            ),

            "atr": round(
                atr_score,
                4,
            ),

            "range": round(
                range_score,
                4,
            ),

            "volume": round(
                volume_score,
                4,
            ),

            "order_flow": round(
                order_flow_score,
                4,
            ),
        },
    }

    return result


# ============================================================================
# Row helper
# ============================================================================

def calculate_risk_from_row(
    row: Any,
) -> dict:
    """
    Calculate risk directly from a Pandas Series-like row.

    This is the function Spark's process_batch() will use.
    """

    features = {
        "vol_20": row.get(
            "vol_20"
        ),

        "vol_60": row.get(
            "vol_60"
        ),

        "atr_pct": row.get(
            "atr_pct"
        ),

        "range_pct": row.get(
            "range_pct"
        ),

        "volume_z_20": row.get(
            "volume_z_20"
        ),

        "order_flow_imbalance": row.get(
            "order_flow_imbalance"
        ),
    }

    return calculate_risk(
        features
    )


# ============================================================================
# Standalone test
# ============================================================================

def main():
    """
    Basic deterministic test for the risk engine.
    """

    print("=" * 70)
    print("RTA RISK ENGINE V1 TEST")
    print("=" * 70)

    sample_features = {
        "vol_20": 0.008,
        "vol_60": 0.006,
        "atr_pct": 0.009,
        "range_pct": 0.007,
        "volume_z_20": 1.5,
        "order_flow_imbalance": 0.25,
    }

    result = calculate_risk(
        sample_features
    )

    print(
        f"Score  : {result['score']}"
    )

    print(
        f"Level  : {result['level']}"
    )

    print(
        f"Source : {result['source']}"
    )

    print()

    print("Components:")

    for key, value in result[
        "components"
    ].items():

        print(
            f"  {key:15s}: {value:.4f}"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()