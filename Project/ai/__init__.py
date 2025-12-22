"""
AI Package Initialization.

This module serves as the entry point for the 'ai' package. It exposes the 
core AI client class, simplifying imports for the rest of the application 
(e.g., allowing `from ai import AIClient` instead of `from ai.ai_client import AIClient`).
"""

# Import the main AI client class to make it available at the package level
from .ai_client import AIClient

# Define the public API of this package.
# This explicitly controls what is imported when a user runs `from Project.ai import *`,
# keeping the namespace clean and internal helpers hidden.
__all__ = ["AIClient"]