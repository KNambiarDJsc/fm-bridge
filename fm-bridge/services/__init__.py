"""
FM Trading Agency — Bridge Services
===================================
Contains core business logic modules for the bridge, including market data,
options chain, indicators, session state, and external intelligence APIs.
"""

from .external_intel import get_full_external_intel

__all__ = [
    "get_full_external_intel",
]
