import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB")

    EMBED_MODEL = "models/text-embedding-004"
    LLM_MODEL = "models/gemini-flash-latest"

    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    LANGFUSE_ENABLED = os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() == "true"
    LANGFUSE_ENV = os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "dev")

    @staticmethod
    def validate():
        if not Config.GOOGLE_API_KEY:
            raise RuntimeError("Missing GOOGLE_API_KEY in .env")
        if not Config.MONGO_URI or not Config.MONGO_DB:
            raise RuntimeError("Missing MONGO_URI or MONGO_DB in .env")

        if Config.LANGFUSE_ENABLED:
            if not Config.LANGFUSE_PUBLIC_KEY or not Config.LANGFUSE_SECRET_KEY:
                raise RuntimeError("Missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY in .env")

