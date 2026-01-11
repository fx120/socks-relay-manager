"""
Proxy Relay System - SOCKS5 proxy relay with automatic health monitoring.
"""

__version__ = "0.1.0"

from .api_client import APIClient, APIError

__all__ = ["APIClient", "APIError", "__version__"]
