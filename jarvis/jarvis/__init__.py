"""Jarvis — a local personal AI assistant with persistent memory.

Runs on the user's own machine, powered by the Claude API, with long-term
memory stored in SQLite. No telemetry.
"""

from .memory import Memory
from .agent import Jarvis

__version__ = "0.1.0"

__all__ = ["Jarvis", "Memory", "__version__"]
