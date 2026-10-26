"""
RTA Anomaly Detection Engine V1

Purpose
-------
Detect unusual cryptocurrency market behaviour from the
50 engineered features for each symbol.

Model
-----
Isolation Forest

Important
---------
This is a global market anomaly detector.
It is NOT user-specific.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

import numpy as np
from sklearn.ensemble import IsolationForest


LOGGER = logging.getLogger("anomaly_engine")


# ============================================================
# CONFIGURATION
# ============================================================

ANOMALY_SOURCE = "ISOLATION_FOREST_V1"

# Number of engineered features per symbol.
FEATURE_COUNT = 50

# Isolation Forest configuration.
N_ESTIMATORS = 200
CONTAMINATION = 0.05
RANDOM_STATE = 42

# Score threshold used for the normalized anomaly score.
# Higher score = more unusual.
ANOMALY_THRESHOLD = 50.0


# ============================================================
# FEATURE ORDER
# ============================================================

FEATURE_COLUMNS = [
    "log_ret_1",
    "ret_1",
    "ret_5",
    "ret_15",
    "ret_30",
    "ret_60",
    "ret_lag_1",
    "ret_lag_2",
    "ret_lag_3",
    "ret_lag_5",
    "ret_lag_10",
    "ret_lag_15",
    "ret_lag_30",
    "ret_lag_60",
    "dist_sma_5",
    "dist_sma_10",
    "dist_sma_20",
    "dist_sma_50",
    "dist_sma_100",
    "dist_ema_5",
    "dist_ema_10",
    "dist_ema_20",
    "dist_ema_50",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "vol_5",
    "vol_15",
    "vol_20",
    "vol_60",
    "vol_ratio_20_60",
    "atr_14",
    "atr_pct",
    "range_pct",
    "body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "volume_change",
    "volume_z_20",
    "quote_volume_change",
    "trade_count_change",
    "taker_buy_ratio",
    "order_flow_imbalance",
    "ofi_mean_15",
    "ofi_mean_60",
    "tod_sin",
    "tod_cos",
    "dow_sin",
    "dow_cos",
]


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value: Any) -> float:
    """Convert a value to float safely."""
    try:
        result = float(value)

        if not np.isfinite(result):
            return 0.0

        return result

    except (TypeError, ValueError):
        return 0.0


def _extract_features(row: Any) -> np.ndarray:
    """
    Extract the exact 50 engineered features from a row.
    """

    values = []

    for column in FEATURE_COLUMNS:
        if hasattr(row, "get"):
            value = row.get(column, 0.0)
        else:
            value = getattr(row, column, 0.0)

        values.append(_safe_float(value))

    features = np.asarray(values, dtype=np.float64)

    if features.shape != (FEATURE_COUNT,):
        raise ValueError(
            f"Expected {FEATURE_COUNT} features, "
            f"got shape {features.shape}"
        )

    return features


# ============================================================
# ANOMALY ENGINE
# ============================================================

class AnomalyEngine:
    """
    Isolation Forest anomaly detector.

    The model is fitted on a rolling batch of engineered
    market observations and then evaluates the latest row.
    """

    def __init__(
        self,
        n_estimators: int = N_ESTIMATORS,
        contamination: float = CONTAMINATION,
        random_state: int = RANDOM_STATE,
    ) -> None:

        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )

        self.is_fitted = False

    # --------------------------------------------------------
    # FIT
    # --------------------------------------------------------

    def fit(self, feature_matrix: Iterable[Iterable[float]]) -> "AnomalyEngine":
        """
        Fit Isolation Forest on historical/rolling observations.

        Parameters
        ----------
        feature_matrix:
            Shape (N, 50)
        """

        X = np.asarray(feature_matrix, dtype=np.float64)

        if X.ndim != 2:
            raise ValueError(
                f"Expected 2D feature matrix, got shape {X.shape}"
            )

        if X.shape[1] != FEATURE_COUNT:
            raise ValueError(
                f"Expected {FEATURE_COUNT} features, "
                f"got {X.shape[1]}"
            )

        X = np.nan_to_num(
            X,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        self.model.fit(X)

        self.is_fitted = True

        LOGGER.info(
            "Isolation Forest fitted | samples=%d | features=%d",
            X.shape[0],
            X.shape[1],
        )

        return self

    # --------------------------------------------------------
    # PREDICT
    # --------------------------------------------------------

    def predict(self, feature_vector: Iterable[float]) -> Dict[str, Any]:
        """
        Evaluate one 50-feature vector.
        """

        if not self.is_fitted:
            raise RuntimeError(
                "AnomalyEngine must be fitted before prediction."
            )

        X = np.asarray(feature_vector, dtype=np.float64)

        if X.shape != (FEATURE_COUNT,):
            raise ValueError(
                f"Expected feature vector shape "
                f"({FEATURE_COUNT},), got {X.shape}"
            )

        X = np.nan_to_num(
            X,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        X_2d = X.reshape(1, -1)

        # Isolation Forest:
        #   positive decision score -> normal
        #   negative decision score -> anomalous
        decision_score = float(
            self.model.decision_function(X_2d)[0]
        )

        raw_prediction = int(
            self.model.predict(X_2d)[0]
        )

        # Convert the Isolation Forest decision score
        # into an intuitive 0-100 anomaly score.
        #
        # Larger value = more unusual.
        anomaly_score = float(
            np.clip(
                50.0 - (decision_score * 100.0),
                0.0,
                100.0,
            )
        )

        is_anomaly = (
            raw_prediction == -1
            or anomaly_score >= ANOMALY_THRESHOLD
        )

        return {
            "score": round(anomaly_score, 4),
            "is_anomaly": bool(is_anomaly),
            "source": ANOMALY_SOURCE,
            "raw_decision_score": round(decision_score, 6),
        }


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def calculate_anomaly(
    feature_matrix: Iterable[Iterable[float]],
    latest_features: Iterable[float],
) -> Dict[str, Any]:
    """
    Fit a V1 Isolation Forest on the supplied observations
    and evaluate the latest observation.

    This is intentionally deterministic through RANDOM_STATE.
    """

    engine = AnomalyEngine()

    engine.fit(feature_matrix)

    return engine.predict(latest_features)


def calculate_anomaly_from_row(
    history_rows: Iterable[Any],
    latest_row: Any,
) -> Dict[str, Any]:
    """
    Convenience wrapper for Pandas-like rows.

    history_rows:
        Collection of rows containing the 50 engineered features.

    latest_row:
        Latest engineered row to evaluate.
    """

    history_features = [
        _extract_features(row)
        for row in history_rows
    ]

    latest_features = _extract_features(latest_row)

    return calculate_anomaly(
        history_features,
        latest_features,
    )


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("RTA ISOLATION FOREST ANOMALY ENGINE V1 TEST")
    print("=" * 70)

    rng = np.random.default_rng(RANDOM_STATE)

    # Synthetic normal observations.
    X_normal = rng.normal(
        loc=0.0,
        scale=0.01,
        size=(200, FEATURE_COUNT),
    )

    # Create one deliberately unusual observation.
    X_anomaly = rng.normal(
        loc=0.0,
        scale=0.01,
        size=(1, FEATURE_COUNT),
    )

    X_anomaly[0, 0] = 1.0
    X_anomaly[0, 24] = 100.0
    X_anomaly[0, 39] = 10.0

    X_train = np.vstack([
        X_normal,
        X_anomaly,
    ])

    engine = AnomalyEngine()
    engine.fit(X_train)

    normal_result = engine.predict(X_normal[-1])
    anomaly_result = engine.predict(X_anomaly[0])

    print()
    print("Normal observation")
    print(f"Score            : {normal_result['score']}")
    print(f"Is anomaly       : {normal_result['is_anomaly']}")
    print(f"Raw decision     : {normal_result['raw_decision_score']}")
    print(f"Source            : {normal_result['source']}")

    print()
    print("Artificial anomaly")
    print(f"Score            : {anomaly_result['score']}")
    print(f"Is anomaly       : {anomaly_result['is_anomaly']}")
    print(f"Raw decision     : {anomaly_result['raw_decision_score']}")
    print(f"Source            : {anomaly_result['source']}")

    print()
    print("=" * 70)
    print("ANOMALY ENGINE TEST COMPLETE")
    print("=" * 70)