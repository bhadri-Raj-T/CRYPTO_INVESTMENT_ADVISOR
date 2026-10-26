"""RTA V4 real-time Spark runtime.

Runtime flow:
Binance -> Kafka -> Spark 1m candles -> exact V4 feature engineering ->
4 independent GRU V4 models -> risk/anomaly -> MongoDB.

Unlike the earlier V3 runtime, V4 does not build one 60x200 cross-asset matrix.
Each asset uses its own 60x50 sequence, matching the final training design.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json

from analytics.anomaly.anomaly_engine import AnomalyEngine
from analytics.risk.risk_engine import calculate_risk_from_row
from streaming.features import engineer_features, get_feature_columns
from streaming.gru_inference import SUPPORTED_SYMBOLS, predict_gru, warmup_models
from streaming.mongo_writer import build_analytics_document, write_analytics_batch
from streaming.schema import tick_schema

os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("rta_v4_stream")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "crypto-ticks")
CHECKPOINT_LOCATION = os.getenv(
    "RTA_SPARK_CHECKPOINT",
    str(PROJECT_ROOT / "checkpoints" / "crypto_features_v4_runtime"),
)
BOOTSTRAP_DATA_DIR = Path(
    os.getenv("RTA_BOOTSTRAP_DATA_DIR", str(PROJECT_ROOT / "runtime_assets" / "bootstrap"))
)

SYMBOLS = list(SUPPORTED_SYMBOLS)
SEQ_LEN = 60
FEATURES_PER_SYMBOL = 50
RAW_HISTORY_ROWS = 240
ANOMALY_HISTORY_ROWS = 180
ONE_MINUTE_US = 60_000_000

symbol_history: dict[str, pd.DataFrame] = {}
latest_feature_rows: dict[str, pd.DataFrame] = {}

REQUIRED_KLINE_COLUMNS = [
    "open_time",
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


def dataframe_has_rows(df) -> bool:
    return len(df.limit(1).collect()) > 0


def validate_feature_contract() -> list[str]:
    features = get_feature_columns()
    if len(features) != FEATURES_PER_SYMBOL:
        raise RuntimeError(
            f"V4 feature contract mismatch: expected {FEATURES_PER_SYMBOL}, got {len(features)}"
        )
    LOGGER.info("V4 feature contract validated: %d features per asset", len(features))
    return features


def _clean_raw_history(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    for column in REQUIRED_KLINE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=REQUIRED_KLINE_COLUMNS)
    return (
        frame.sort_values("open_time")
        .drop_duplicates(subset=["open_time"], keep="last")
        .tail(RAW_HISTORY_ROWS)
        .reset_index(drop=True)
    )


def bootstrap_historical_state() -> None:
    feature_columns = get_feature_columns()
    LOGGER.info("=" * 72)
    LOGGER.info("RTA V4 RUNTIME BOOTSTRAP")
    LOGGER.info("Bootstrap directory: %s", BOOTSTRAP_DATA_DIR)
    LOGGER.info("=" * 72)

    for symbol in SYMBOLS:
        path = BOOTSTRAP_DATA_DIR / f"{symbol}_1m.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"Missing runtime bootstrap: {path}. Run PREPARE_RUNTIME_ASSETS.bat first."
            )

        history = pd.read_parquet(path, columns=REQUIRED_KLINE_COLUMNS)
        history = _clean_raw_history(history)
        if len(history) < 160:
            raise RuntimeError(
                f"{symbol}: runtime bootstrap has only {len(history)} rows. Need at least 160."
            )

        symbol_history[symbol] = history
        enriched = engineer_features(history.copy(), include_target=False)
        latest_feature_rows[symbol] = enriched[["open_time", *feature_columns]].copy()

        seq, reason = build_asset_sequence(symbol)
        LOGGER.info(
            "Bootstrap | %s | raw=%d | engineered=%d | sequence=%s | %s",
            symbol,
            len(history),
            len(enriched),
            None if seq is None else seq.shape,
            reason,
        )

    LOGGER.info("Historical runtime bootstrap complete.")


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("RTA_GRU_V4_Runtime")
        .config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0",
        )
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.sql.execution.arrow.pyspark.enabled", "false")
        .getOrCreate()
    )


def read_kafka_stream(spark: SparkSession):
    raw_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .option("maxOffsetsPerTrigger", 1000)
        .load()
    )
    return (
        raw_df
        .selectExpr("CAST(value AS STRING) AS json_str")
        .select(from_json(col("json_str"), tick_schema).alias("data"))
        .select("data.*")
    )


def prepare_klines(batch_df) -> pd.DataFrame:
    klines_df = (
        batch_df
        .filter(col("stream_type") == "kline")
        .filter(col("kline_interval") == "1m")
        .filter(col("kline_is_closed") == True)
        .filter(col("symbol").isin(SYMBOLS))
        .select(
            "symbol",
            "kline_start_time",
            "kline_open",
            "kline_high",
            "kline_low",
            "kline_close",
            "kline_volume",
            "kline_quote_volume",
            "kline_num_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
        )
    )
    if not dataframe_has_rows(klines_df):
        return pd.DataFrame()

    pdf = klines_df.toPandas()
    if pdf.empty:
        return pdf

    pdf = pdf.rename(
        columns={
            "kline_start_time": "open_time",
            "kline_open": "open",
            "kline_high": "high",
            "kline_low": "low",
            "kline_close": "close",
            "kline_volume": "volume",
            "kline_quote_volume": "quote_asset_volume",
            "kline_num_trades": "num_trades",
        }
    )
    for column in REQUIRED_KLINE_COLUMNS:
        pdf[column] = pd.to_numeric(pdf[column], errors="coerce")

    # Binance websocket uses milliseconds. V4 features/training use microseconds.
    pdf["open_time"] = (pdf["open_time"] * 1000).astype("int64")
    pdf["symbol"] = pdf["symbol"].astype(str).str.upper()
    pdf = pdf.dropna(subset=REQUIRED_KLINE_COLUMNS)
    return (
        pdf.sort_values(["symbol", "open_time"])
        .drop_duplicates(subset=["symbol", "open_time"], keep="last")
        .reset_index(drop=True)
    )


def build_asset_sequence(symbol: str) -> tuple[np.ndarray | None, str]:
    frame = latest_feature_rows.get(symbol)
    if frame is None or frame.empty:
        return None, "NO_FEATURE_HISTORY"

    features = get_feature_columns()
    clean = (
        frame[["open_time", *features]]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .sort_values("open_time")
    )
    if len(clean) < SEQ_LEN:
        return None, f"WARMING_UP_{len(clean)}_OF_{SEQ_LEN}"

    tail = clean.tail(SEQ_LEN)
    times = pd.to_numeric(tail["open_time"], errors="coerce").to_numpy(dtype=np.int64)
    if len(times) != SEQ_LEN or np.any(np.diff(times) != ONE_MINUTE_US):
        return None, "SEQUENCE_GAP"

    sequence = tail[features].to_numpy(dtype=np.float32, copy=True)
    if sequence.shape != (SEQ_LEN, FEATURES_PER_SYMBOL):
        return None, f"BAD_SHAPE_{sequence.shape}"
    if not np.isfinite(sequence).all():
        return None, "NONFINITE_SEQUENCE"
    return sequence, "READY"


def calculate_live_anomaly(history_df: pd.DataFrame, latest_row: pd.Series) -> dict:
    try:
        feature_columns = get_feature_columns()
        history_features = (
            history_df[feature_columns]
            .tail(ANOMALY_HISTORY_ROWS)
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
        )
        if len(history_features) < 50:
            return {
                "score": None,
                "is_anomaly": None,
                "source": "ISOLATION_FOREST_V1",
                "status": "INSUFFICIENT_DATA",
            }

        latest_features = (
            latest_row[feature_columns]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
            .to_numpy(dtype=np.float64)
        )
        engine = AnomalyEngine()
        engine.fit(history_features.to_numpy(dtype=np.float64))
        result = engine.predict(latest_features)
        result["status"] = "OK"
        return result
    except Exception:
        LOGGER.exception("Live anomaly calculation failed")
        return {
            "score": None,
            "is_anomaly": None,
            "source": "ISOLATION_FOREST_V1",
            "status": "ERROR",
        }


def _prediction_unavailable(reason: str) -> dict:
    return {
        "value": None,
        "predicted_log_return": None,
        "direction": None,
        "return_direction": None,
        "probability_up": None,
        "probability_down": None,
        "confidence": None,
        "signal": "UNAVAILABLE",
        "source": "GRU_V4_ASSET_SPECIFIC_EXPERIMENTAL",
        "model_version": "GRU_V4",
        "forecast_horizon_minutes": 15,
        "status": reason,
    }


def process_batch(batch_df, batch_id: int) -> None:
    if not dataframe_has_rows(batch_df):
        LOGGER.info("Batch %s | empty", batch_id)
        return

    batch_df = batch_df.cache()
    try:
        pdf = prepare_klines(batch_df)
        if pdf.empty:
            LOGGER.info("Batch %s | no closed 1m klines", batch_id)
            return

        LOGGER.info("Batch %s | %d closed 1m klines", batch_id, len(pdf))
        feature_columns = get_feature_columns()
        documents: list[dict] = []

        for symbol, incoming in pdf.groupby("symbol"):
            incoming = (
                incoming.sort_values("open_time")
                .drop_duplicates(subset=["open_time"], keep="last")
                .reset_index(drop=True)
            )
            previous = symbol_history.get(symbol)
            combined = incoming.copy() if previous is None else pd.concat(
                [previous, incoming], ignore_index=True
            )
            combined = _clean_raw_history(combined)
            symbol_history[symbol] = combined.copy()

            try:
                enriched = engineer_features(combined.copy(), include_target=False)
            except Exception:
                LOGGER.exception("Batch %s | %s | feature engineering failed", batch_id, symbol)
                continue
            if enriched.empty:
                continue

            latest_feature_rows[symbol] = enriched[["open_time", *feature_columns]].copy()
            latest = enriched.iloc[-1]
            sequence, seq_status = build_asset_sequence(symbol)

            if sequence is None:
                prediction = _prediction_unavailable(seq_status)
            else:
                try:
                    prediction = predict_gru(symbol, sequence)
                except Exception as exc:
                    LOGGER.exception("Batch %s | %s | GRU V4 inference failed", batch_id, symbol)
                    prediction = _prediction_unavailable(f"INFERENCE_ERROR: {exc}")

            risk = calculate_risk_from_row(latest)
            anomaly = calculate_live_anomaly(latest_feature_rows[symbol], latest)
            feature_values = {name: latest.get(name) for name in feature_columns}

            document = build_analytics_document(
                symbol=symbol,
                row=latest,
                features=feature_values,
                prediction=prediction,
                risk=risk,
                anomaly=anomaly,
                metadata={
                    "pipeline": "RTA_V4",
                    "source": "spark_stream",
                    "model_family": "GRU",
                    "model_version": "GRU_V4",
                    "feature_count": FEATURES_PER_SYMBOL,
                    "sequence_length": SEQ_LEN,
                    "forecast_horizon_minutes": 15,
                    "test_record": False,
                },
            )
            documents.append(document)

            LOGGER.info(
                "Batch %s | %s | close=%.6f | model=%s | dir=%s | p_up=%s | risk=%s | anomaly=%s",
                batch_id,
                symbol,
                float(latest["close"]),
                prediction.get("status"),
                prediction.get("direction"),
                None if prediction.get("probability_up") is None else round(float(prediction["probability_up"]), 4),
                risk.get("level"),
                anomaly.get("is_anomaly"),
            )

        if documents:
            written = write_analytics_batch(documents)
            LOGGER.info("Batch %s | MongoDB documents written=%d", batch_id, written)
    finally:
        batch_df.unpersist()


def run() -> None:
    validate_feature_contract()

    model_status = warmup_models()
    LOGGER.info("GRU V4 model status: %s", model_status)
    failed = {k: v for k, v in model_status.items() if v != "READY"}
    if failed and os.getenv("RTA_ALLOW_PARTIAL_MODELS", "0") != "1":
        raise RuntimeError(
            "One or more V4 model assets are unavailable. "
            "Run PREPARE_RUNTIME_ASSETS.bat. Failures: " + str(failed)
        )

    bootstrap_historical_state()
    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    LOGGER.info("=" * 72)
    LOGGER.info("RTA LIVE SPARK V4 | FOUR ASSET-SPECIFIC GRU MODELS")
    LOGGER.info("Kafka      : %s", KAFKA_BOOTSTRAP_SERVERS)
    LOGGER.info("Topic      : %s", KAFKA_TOPIC)
    LOGGER.info("Symbols    : %s", ", ".join(SYMBOLS))
    LOGGER.info("Model input: %d x %d per asset", SEQ_LEN, FEATURES_PER_SYMBOL)
    LOGGER.info("Checkpoint : %s", CHECKPOINT_LOCATION)
    LOGGER.info("=" * 72)

    parsed_df = read_kafka_stream(spark)
    query = (
        parsed_df.writeStream
        .foreachBatch(process_batch)
        .outputMode("update")
        .option("checkpointLocation", CHECKPOINT_LOCATION)
        .start()
    )

    LOGGER.info("Spark streaming query started. Waiting for closed Binance 1m klines.")
    try:
        query.awaitTermination()
    except KeyboardInterrupt:
        LOGGER.info("Stopping Spark runtime...")
        try:
            query.stop()
        except Exception:
            pass
        try:
            spark.stop()
        except Exception:
            pass


if __name__ == "__main__":
    run()
