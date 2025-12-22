# Project/utils/observability.py
import os
from typing import Optional

from langfuse import get_client

# Global flag to prevent log spamming.
# We only want to warn the user about missing keys once per application lifecycle,
# not on every single API request.
_warned_missing_keys = False

def _truthy(v: str | None) -> bool:
    """
    Helper to robustly parse boolean-like environment variables.
    Handles 'true', '1', 'yes', 'on' (case-insensitive).
    """
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}

def get_langfuse():
    """
    Retrieves the Langfuse Client for distributed tracing.

    Design Pattern: Safe Factory
    This function is designed to never raise an exception. If observability 
    is disabled or misconfigured, it returns `None`. The calling code 
    (decorators in `agent_tools.py`) checks for `None` and skips tracing logic 
    accordingly, ensuring that observability issues never break core business logic.

    Returns:
        Langfuse | None: The client instance if configured, otherwise None.
    """
    global _warned_missing_keys

    # Feature Flag: Check if tracing is globally enabled
    enabled = _truthy(os.getenv("LANGFUSE_TRACING_ENABLED", "true"))
    if not enabled:
        return None

    # Credentials Check:
    # We rely on the standard Langfuse env vars (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY).
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    
    if not public_key or not secret_key:
        # Idempotent Warning: Log this error only once.
        if not _warned_missing_keys:
            print("[Langfuse] Tracing enabled but LANGFUSE_PUBLIC_KEY/SECRET_KEY missing. Tracing disabled.")
            _warned_missing_keys = True
        return None

    # Initialize the client (it automatically picks up keys from os.environ)
    return get_client()

def get_langfuse_env() -> str:
    """
    Returns the current environment tag (e.g., 'dev', 'staging', 'prod').
    Used to filter traces in the Langfuse dashboard.
    """
    return os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "dev")