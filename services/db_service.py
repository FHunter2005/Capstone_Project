from pymongo import MongoClient
from utils.config import Config

class DatabaseService:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI)
        self.db = self.client[Config.MONGO_DB]

    def masters(self):
        return self.db.Masters

    def locations(self):
        return self.db.Maps_Location
