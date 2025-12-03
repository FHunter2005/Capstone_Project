import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB")
    EMBED_MODEL = "models/text-embedding-004"
    LLM_MODEL = "gemini-2.0-flash"

    @staticmethod
    def validate():
        if not Config.GOOGLE_API_KEY:
            raise RuntimeError("Missing GOOGLE_API_KEY in .env")
        if not Config.MONGO_URI or not Config.MONGO_DB:
            raise RuntimeError("Missing MONGO_URI or MONGO_DB in .env")
