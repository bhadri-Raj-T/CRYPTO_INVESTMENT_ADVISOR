from api.database import realtime_analytics_collection

REALTIME_ANALYTICS_COLLECTION = "realtime_analytics"


def get_realtime_analytics_collection():
    return realtime_analytics_collection


def create_realtime_analytics_indexes():
    collection = get_realtime_analytics_collection()
    collection.create_index(
        [("symbol", 1), ("timestamp", -1)],
        unique=True,
        name="symbol_timestamp_unique",
    )
    collection.create_index(
        [("anomaly.is_anomaly", 1), ("timestamp", -1)],
        name="anomaly_timestamp",
    )
    collection.create_index(
        [("prediction.model_version", 1), ("symbol", 1), ("timestamp", -1)],
        name="model_symbol_timestamp",
    )
    return collection
