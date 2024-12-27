"""
Minimax Python SDK - Unofficial Python library for the Minimax REST API
"""

from importlib.metadata import version

from .client import AsyncMinimax, Minimax
from .exceptions import MinimaxAPIError, MinimaxError

__version__ = version("minimax-python")
__all__ = ["Minimax", "AsyncMinimax", "MinimaxError", "MinimaxAPIError"]
