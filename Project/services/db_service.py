# Project/services/db_service.py
from pymongo import MongoClient
import os
from utils.config import Config

class DatabaseService:
    """
    MongoDB Database Access Layer (Singleton).

    This class serves as the single source of truth for database connections.
    It implements the Singleton design pattern to ensure that the application
    maintains only ONE connection pool to MongoDB, rather than opening a new
    connection for every request (which would overwhelm the database).
    """
    
    _instance = None 

    def __new__(cls):
        """
        Constructor override to enforce the Singleton pattern.
        
        If an instance already exists, it returns it.
        If not, it creates the connection using credentials from Config.
        """
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
            
            # Fallback logic: Try Config object first, then environment variables
            uri = Config.MONGO_URI or os.getenv("MONGO_URI")
            
            # Initialize the MongoClient once. 
            # MongoClient handles connection pooling internally.
            cls._instance.client = MongoClient(uri)
            cls._instance.db = cls._instance.client[Config.MONGO_DB]
            
        return cls._instance

    # --- Collection Accessors ---
    # These helper methods provide clean access to specific collections,
    # preventing typo-related bugs (e.g., using "Users" instead of "users").

    def users(self): 
        """Returns the 'users' collection (Authentication & Profiles)."""
        return self.db["users"]
        
    def masters(self): 
        """Returns the 'Masters' collection (University Programs & Vectors)."""
        return self.db["Masters"]
        
    def chat_logs(self): 
        """Returns the 'chat_logs' collection (Conversation History)."""
        return self.db["chat_logs"]
        
    def maps_location(self):
        """Returns the 'Maps_Location' collection (Geospatial data for visualisations)."""
        return self.db["Maps_Location"]