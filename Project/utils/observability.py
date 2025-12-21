# utils/observability.py
import os
from typing import Optional

from langfuse import get_client

_warned_missing_keys = False

def _truthy(v: str | None) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}

def get_langfuse():
    """
    Returns Langfuse client (OTel-based) or None if disabled/misconfigured.
    """
    global _warned_missing_keys

    enabled = _truthy(os.getenv("LANGFUSE_TRACING_ENABLED", "true"))
    if not enabled:
        return None

    # With get_client(), keys are expected to come from env vars
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        if not _warned_missing_keys:
            print("[Langfuse] Tracing enabled but LANGFUSE_PUBLIC_KEY/SECRET_KEY missing. Tracing disabled.")
            _warned_missing_keys = True
        return None

    return get_client()

def get_langfuse_env() -> str:
    return os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "dev")
