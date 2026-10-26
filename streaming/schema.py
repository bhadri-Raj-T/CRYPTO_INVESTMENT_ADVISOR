# streaming/schema.py

from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    LongType,
    DoubleType,
    BooleanType,
    IntegerType,
)


tick_schema = StructType([
    # -----------------------------------------------------------------------
    # Common
    # -----------------------------------------------------------------------
    StructField("stream_type", StringType(), True),
    StructField("symbol", StringType(), True),
    StructField("event_time", LongType(), True),

    # -----------------------------------------------------------------------
    # Trade fields
    # -----------------------------------------------------------------------
    StructField("trade_id", LongType(), True),
    StructField("price", DoubleType(), True),
    StructField("quantity", DoubleType(), True),
    StructField("buyer_order_id", StringType(), True),
    StructField("seller_order_id", StringType(), True),
    StructField("trade_time", LongType(), True),
    StructField("is_buyer_maker", BooleanType(), True),

    # -----------------------------------------------------------------------
    # Kline fields
    # -----------------------------------------------------------------------
    StructField("kline_start_time", LongType(), True),
    StructField("kline_close_time", LongType(), True),
    StructField("kline_interval", StringType(), True),

    StructField("kline_open", DoubleType(), True),
    StructField("kline_high", DoubleType(), True),
    StructField("kline_low", DoubleType(), True),
    StructField("kline_close", DoubleType(), True),

    StructField("kline_volume", DoubleType(), True),
    StructField("kline_num_trades", IntegerType(), True),
    StructField("kline_is_closed", BooleanType(), True),
    StructField("kline_quote_volume", DoubleType(), True),

    # -----------------------------------------------------------------------
    # Required by training feature pipeline
    # -----------------------------------------------------------------------
    StructField("taker_buy_base_volume", DoubleType(), True),
    StructField("taker_buy_quote_volume", DoubleType(), True),
])