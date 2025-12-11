# services/db_service.py
from pymongo import MongoClient
from utils.config import Config


class DatabaseService:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI)
        self.db = self.client[Config.MONGO_DB]

    def masters(self):
        return self.db["Masters"]

    def maps_location(self):
        return self.db["Maps_Location"]
    
    def users(self):
        return self.db["users"]

    def chat_logs(self):
        return self.db["chat_logs"]