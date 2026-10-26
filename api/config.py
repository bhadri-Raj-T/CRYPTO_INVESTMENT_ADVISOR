import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017",
)

MONGO_DB = os.getenv(
    "MONGO_DB",
    "rta",
)

REALTIME_COLLECTION = "realtime_analytics"
USERS_COLLECTION = "users"
TRANSACTIONS_COLLECTION = "transactions"
ALERTS_COLLECTION = "alerts"

JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "rta-development-secret-change-later",
)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60