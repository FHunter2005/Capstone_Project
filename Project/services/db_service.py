# Project/services/db_service.py
from pymongo import MongoClient
import os
from utils.config import Config

class DatabaseService:
    _instance = None  # This stores the single instance

    def __new__(cls):
        """
        Ensures only one instance of the database client exists.
        """
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
            # Use the URI from your Config or .env
            uri = Config.MONGO_URI or os.getenv("MONGO_URI")
            # The client is initialized ONLY ONCE here
            cls._instance.client = MongoClient(uri)
            cls._instance.db = cls._instance.client[Config.MONGO_DB]
        return cls._instance

    # Methods to access specific collections
    def users(self): 
        return self.db["users"]
        
    def masters(self): 
        return self.db["Masters"]
        
    def chat_logs(self): 
        return self.db["chat_logs"]
        
    def maps_location(self):
        return self.db["Maps_Location"]