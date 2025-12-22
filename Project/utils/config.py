# Project/utils/config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file into os.environ at import time
load_dotenv()


class Config:
    """
    Centralized Application Configuration.

    This class serves as the single source of truth for all infrastructure credentials,
    AI model settings, and observability configurations. It abstracts `os.getenv` 
    calls, providing a clean interface for the rest of the application to access 
    runtime settings.
    """

    # --- Infrastructure Credentials ---
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB")

    # --- AI Model Definitions ---
    # Hardcoding specific model versions ensures consistency across environments.
    EMBED_MODEL = "models/text-embedding-004"
    LLM_MODEL = "models/gemini-flash-latest"

    # --- Observability (Langfuse) ---
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    
    # Feature Flag: Allows toggling tracing on/off without changing code (defaults to True)
    LANGFUSE_ENABLED = os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() == "true"
    LANGFUSE_ENV = os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "dev")

    @staticmethod
    def validate():
        """
        'Fail Fast' Configuration Validation.

        This method checks for the presence of critical environment variables 
        at application startup. If any required keys are missing, it raises 
        a RuntimeError immediately.
        
        Why this matters: It prevents the application from starting in a 
        partially broken state (e.g., running fine until a user tries to chat, 
        then crashing because the API key is missing).
        """
        if not Config.GOOGLE_API_KEY:
            raise RuntimeError("CRITICAL: Missing GOOGLE_API_KEY in .env")
        
        if not Config.MONGO_URI or not Config.MONGO_DB:
            raise RuntimeError("CRITICAL: Missing MONGO_URI or MONGO_DB in .env")

        # Conditional Validation: Only check Langfuse keys if tracing is actually enabled.
        if Config.LANGFUSE_ENABLED:
            if not Config.LANGFUSE_PUBLIC_KEY or not Config.LANGFUSE_SECRET_KEY:
                raise RuntimeError("CRITICAL: Tracing is enabled but LANGFUSE keys are missing.")