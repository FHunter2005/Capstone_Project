"""
AI package – Gemini API client and prompts.
"""

from .ai_client import AIClient
from .prompts import elaboration_prompt

__all__ = ["AIClient", "elaboration_prompt"]
