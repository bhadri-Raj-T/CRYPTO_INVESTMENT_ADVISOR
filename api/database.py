from pymongo import MongoClient
from api.config import MONGO_URI, MONGO_DB

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

users_collection = db["users"]
transactions_collection = db["transactions"]
realtime_analytics_collection = db["realtime_analytics"]
alerts_collection = db["alerts"]

def check_database():
    client.admin.command("ping")
    return True
