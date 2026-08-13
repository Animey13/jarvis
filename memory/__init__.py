"""
JARVIS Memory Subpackage.

This package implements short-term, episodic, and long-term memory structures,
utilizing local vector/document databases or file-based mechanisms.
"""

from memory.base import BaseMemory
from memory.local_json import LocalJSONMemory

__all__ = [
    "BaseMemory",
    "LocalJSONMemory",
]
