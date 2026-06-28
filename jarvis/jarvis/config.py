"""Configuration constants and helpers for Jarvis.

All settings are resolved from the environment with sensible local-first
defaults. There is no telemetry and no network access here.
"""

import os
from pathlib import Path

APP_NAME = "jarvis"

# Latest, most capable model. DO NOT change.
DEFAULT_MODEL = "claude-opus-4-8"
MODEL = os.environ.get("JARVIS_MODEL", DEFAULT_MODEL)

# Home directory for Jarvis state (database, etc.).
JARVIS_HOME = Path(
    os.environ.get("JARVIS_HOME", str(Path.home() / ".jarvis"))
).expanduser()
DB_PATH = JARVIS_HOME / "jarvis.db"

MAX_TOKENS = 4096

BASE_SYSTEM_PROMPT = (
    "You are Jarvis, a personal AI assistant that runs locally on the user's "
    "own machine. You have a persistent long-term memory. Proactively use the "
    "'remember' tool to save durable facts, preferences, and context about the "
    "user worth recalling later, and the 'recall' tool to look things up before "
    "answering when memory may help. Be concise, warm, and genuinely helpful."
)


def api_key() -> "str | None":
    """Return the Anthropic API key from the environment, or None if unset."""
    return os.environ.get("ANTHROPIC_API_KEY")


def ensure_home() -> None:
    """Create the Jarvis home directory if it does not already exist."""
    JARVIS_HOME.mkdir(parents=True, exist_ok=True)
