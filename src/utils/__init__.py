"""
Utils package - Shared utilities

Configuration, tracing setup, and other cross-cutting concerns.
"""

from .tracing import init_tracing
from .config import load_config

__all__ = ['init_tracing', 'load_config']
