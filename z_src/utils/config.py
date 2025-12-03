"""
Configuration Management - Environment variables and settings

Centralized configuration for the entire application.
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    """Load application configuration from environment variables.

    Returns:
        Dictionary with configuration values

    Example:
        >>> config = load_config()
        >>> model = config.get("MODEL")
        >>> api_key = config.get("GOOGLE_API_KEY")
    """
    load_dotenv()

    config = {
        # Google AI Configuration
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "MODEL": os.getenv("MODEL", "gemini-2.5-flash-lite"),

        # Langfuse Configuration
        "LANGFUSE_PUBLIC_KEY": os.getenv("LANGFUSE_PUBLIC_KEY"),
        "LANGFUSE_SECRET_KEY": os.getenv("LANGFUSE_SECRET_KEY"),
        "LANGFUSE_HOST": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),

        # Application Settings
        "DEBUG": os.getenv("DEBUG", "False").lower() == "true",
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
    }

    # Validate required keys
    if not config["GOOGLE_API_KEY"]:
        raise ValueError("GOOGLE_API_KEY not set in environment")

    return config


def get_model_config() -> Dict[str, Any]:
    """Get model-specific configuration.

    Returns:
        Dictionary with model settings
    """
    return {
        "model": os.getenv("MODEL", "gemini-2.5-flash-lite"),
        "temperature": float(os.getenv("TEMPERATURE", "0.7")),
        "max_output_tokens": int(os.getenv("MAX_OUTPUT_TOKENS", "2048")),
    }
