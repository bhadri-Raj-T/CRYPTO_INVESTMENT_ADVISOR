import numpy as np
import pandas as pd


BASE_FEATURE_COLUMNS = [
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


def safe_pct_change(series: pd.Series) -> pd.Series:
    """
    Percentage change that avoids +/-inf when the previous value is zero.

    Genuine unavailable values remain NaN.
    """
    previous = series.shift(1)

    result = pd.Series(
        np.nan,
        index=series.index,
        dtype="float64",
    )

    valid = (
        series.notna()
        & previous.notna()
        & (previous != 0)
    )

    result.loc[valid] = (
        series.loc[valid] / previous.loc[valid] - 1.0
    )

    return result


def engineer_features(
    df: pd.DataFrame,
    horizon: int = 15,
    include_target: bool = True,
) -> pd.DataFrame:

    df = df.copy()

    # --------------------------------------------------------
    # Basic numeric protection
    # --------------------------------------------------------

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "num_trades",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    close = df["close"]
    volume = df["volume"]

    # --------------------------------------------------------
    # Returns
    # --------------------------------------------------------

    log_close = np.log(
        close.where(close > 0)
    )

    df["log_ret_1"] = log_close.diff()

    df["ret_1"] = safe_pct_change(close)

    for window in [5, 15, 30, 60]:
        previous = close.shift(window)

        result = pd.Series(
            np.nan,
            index=df.index,
            dtype="float64",
        )

        valid = (
            close.notna()
            & previous.notna()
            & (previous != 0)
        )

        result.loc[valid] = (
            close.loc[valid]
            / previous.loc[valid]
            - 1.0
        )

        df[f"ret_{window}"] = result

    for lag in [1, 2, 3, 5, 10, 15, 30, 60]:
        df[f"ret_lag_{lag}"] = (
            df["log_ret_1"].shift(lag)
        )

    # --------------------------------------------------------
    # Moving averages
    # --------------------------------------------------------

    for window in [5, 10, 20, 50, 100]:

        sma = close.rolling(
            window=window,
            min_periods=window,
        ).mean()

        df[f"dist_sma_{window}"] = (
            close / sma.replace(0, np.nan) - 1.0
        )

    for window in [5, 10, 20, 50]:

        ema = close.ewm(
            span=window,
            adjust=False,
        ).mean()

        df[f"dist_ema_{window}"] = (
            close / ema.replace(0, np.nan) - 1.0
        )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(
        window=14,
        min_periods=14,
    ).mean()

    avg_loss = loss.rolling(
        window=14,
        min_periods=14,
    ).mean()

    # Standard RSI edge-case handling:
    #
    # avg_loss == 0 and avg_gain > 0  -> RSI = 100
    # avg_gain == 0 and avg_loss > 0  -> RSI = 0
    # avg_gain == 0 and avg_loss == 0 -> RSI = 50
    # insufficient history              -> NaN

    rsi = pd.Series(
        np.nan,
        index=df.index,
        dtype="float64",
    )

    valid_rsi = (
        avg_gain.notna()
        & avg_loss.notna()
    )

    both_zero = (
        valid_rsi
        & (avg_gain == 0)
        & (avg_loss == 0)
    )

    only_loss_zero = (
        valid_rsi
        & (avg_loss == 0)
        & (avg_gain > 0)
    )

    only_gain_zero = (
        valid_rsi
        & (avg_gain == 0)
        & (avg_loss > 0)
    )

    normal_rsi = (
        valid_rsi
        & (avg_gain > 0)
        & (avg_loss > 0)
    )

    rsi.loc[both_zero] = 50.0
    rsi.loc[only_loss_zero] = 100.0
    rsi.loc[only_gain_zero] = 0.0

    rs = (
        avg_gain.loc[normal_rsi]
        / avg_loss.loc[normal_rsi]
    )

    rsi.loc[normal_rsi] = (
        100.0
        - 100.0 / (1.0 + rs)
    )

    df["rsi_14"] = rsi

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    ema12 = close.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
    ).mean()

    macd = ema12 - ema26

    signal = macd.ewm(
        span=9,
        adjust=False,
    ).mean()

    df["macd"] = macd
    df["macd_signal"] = signal
    df["macd_hist"] = macd - signal

    # --------------------------------------------------------
    # Volatility
    # --------------------------------------------------------

    for window in [5, 15, 20, 60]:

        df[f"vol_{window}"] = (
            df["log_ret_1"]
            .rolling(
                window=window,
                min_periods=window,
            )
            .std()
        )

    df["vol_ratio_20_60"] = (
        df["vol_20"]
        / df["vol_60"].replace(0, np.nan)
    )

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.rolling(
        window=14,
        min_periods=14,
    ).mean()

    df["atr_14"] = atr

    df["atr_pct"] = (
        atr / close.replace(0, np.nan)
    )

    # --------------------------------------------------------
    # Candle structure
    # --------------------------------------------------------

    candle_range = (
        df["high"] - df["low"]
    )

    safe_close = close.replace(0, np.nan)

    df["range_pct"] = (
        candle_range / safe_close
    )

    df["body_pct"] = (
        (df["close"] - df["open"]).abs()
        / safe_close
    )

    df["upper_wick_pct"] = (
        (
            df["high"]
            - df[["open", "close"]].max(axis=1)
        )
        / safe_close
    )

    df["lower_wick_pct"] = (
        (
            df[["open", "close"]].min(axis=1)
            - df["low"]
        )
        / safe_close
    )

    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    df["volume_change"] = safe_pct_change(
        volume
    )

    volume_mean = volume.rolling(
        window=20,
        min_periods=20,
    ).mean()

    volume_std = volume.rolling(
        window=20,
        min_periods=20,
    ).std()

    df["volume_z_20"] = (
        (volume - volume_mean)
        / volume_std.replace(0, np.nan)
    )

    df["quote_volume_change"] = safe_pct_change(
        df["quote_asset_volume"]
    )

    df["trade_count_change"] = safe_pct_change(
        df["num_trades"]
    )

    # --------------------------------------------------------
    # Taker buy ratio
    # --------------------------------------------------------

    buy = df["taker_buy_base_volume"]

    df["taker_buy_ratio"] = (
        buy / volume.replace(0, np.nan)
    )

    # --------------------------------------------------------
    # Order flow
    # --------------------------------------------------------

    sell = volume - buy

    denominator = volume.replace(
        0,
        np.nan,
    )

    df["order_flow_imbalance"] = (
        (buy - sell)
        / denominator
    )

    # --------------------------------------------------------
    # Rolling order-flow features
    # --------------------------------------------------------

    df["ofi_mean_15"] = (
        df["order_flow_imbalance"]
        .rolling(
            window=15,
            min_periods=15,
        )
        .mean()
    )

    df["ofi_mean_60"] = (
        df["order_flow_imbalance"]
        .rolling(
            window=60,
            min_periods=60,
        )
        .mean()
    )

    # --------------------------------------------------------
    # Time-of-day
    # --------------------------------------------------------

    timestamp = pd.to_datetime(
        df["open_time"],
        unit="us",
        utc=True,
    )

    minutes = (
        timestamp.dt.hour * 60
        + timestamp.dt.minute
    )

    df["tod_sin"] = np.sin(
        2 * np.pi * minutes / 1440
    )

    df["tod_cos"] = np.cos(
        2 * np.pi * minutes / 1440
    )

    # --------------------------------------------------------
    # Day-of-week
    # --------------------------------------------------------

    dow = timestamp.dt.dayofweek

    df["dow_sin"] = np.sin(
        2 * np.pi * dow / 7
    )

    df["dow_cos"] = np.cos(
        2 * np.pi * dow / 7
    )

    # --------------------------------------------------------
    # Target
    # --------------------------------------------------------

    if include_target:

        future_timestamp = (
            df["open_time"]
            + horizon * 60 * 1_000_000
        )

        target_map = pd.Series(
            df["close"].values,
            index=df["open_time"].values,
        )

        future_close = future_timestamp.map(
            target_map
        )

        df["future_log_ret"] = (
            np.log(
                future_close.where(
                    future_close > 0
                )
            )
            - log_close
        )

    # --------------------------------------------------------
    # Final numerical cleanup
    # --------------------------------------------------------
    #
    # Convert accidental +/-inf to NaN.
    #
    # IMPORTANT:
    # We do NOT fill NaN values here.
    # Rolling warm-up and genuine missing data
    # must remain identifiable to the dataset builder.

    feature_columns = [
        col
        for col in BASE_FEATURE_COLUMNS
        if col in df.columns
    ]

    df[feature_columns] = (
        df[feature_columns]
        .replace([np.inf, -np.inf], np.nan)
    )

    if include_target:
        df["future_log_ret"] = (
            df["future_log_ret"]
            .replace([np.inf, -np.inf], np.nan)
        )

    return df


def get_feature_columns():
    return BASE_FEATURE_COLUMNS.copy()