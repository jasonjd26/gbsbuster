"""Interactive command-line REPL for Jarvis.

Provides a simple read-eval-print loop with a few slash commands for
inspecting and managing memory. Chat turns are routed through the
:class:`~jarvis.agent.Jarvis` engine. Standard library only.
"""

from . import config
from .memory import Memory

BANNER = "Jarvis — your local assistant. Type /help for commands."

HELP_TEXT = """\
Commands:
  /help            Show this help message
  /memories        List saved memories
  /forget <id>     Delete the memory with the given id
  /exit, /quit     Leave Jarvis

Anything else is sent to Jarvis as a chat message."""

NO_API_KEY_NOTE = """\
Note: ANTHROPIC_API_KEY is not set, so chat is disabled.
To enable chat, set your Anthropic API key and restart, e.g.:

    export ANTHROPIC_API_KEY="sk-ant-..."

The /memories and /help commands still work without a key."""


def _print_memories(memory: Memory) -> None:
    """Print saved memories, newest first."""
    rows = memory.list_memories()
    if not rows:
        print("No memories saved yet.")
        return
    for row in rows:
        kind = row.get("kind") or "note"
        print(f"[{row['id']}] ({kind}) {row['content']}")


def _handle_forget(memory: Memory, arg: str) -> None:
    """Handle the ``/forget <id>`` command."""
    arg = arg.strip()
    if not arg:
        print("Usage: /forget <id>")
        return
    try:
        memory_id = int(arg)
    except ValueError:
        print(f"Invalid id: {arg!r}. Usage: /forget <id>")
        return
    if memory.forget(memory_id):
        print(f"Forgot memory id={memory_id}.")
    else:
        print(f"No memory found with id={memory_id}.")


def main() -> None:
    """Run the Jarvis interactive REPL."""
    config.ensure_home()
    memory = Memory(config.DB_PATH)

    has_key = config.api_key() is not None

    print(BANNER)
    if not has_key:
        print()
        print(NO_API_KEY_NOTE)

    jarvis = None  # created lazily on the first chat turn

    try:
        while True:
            try:
                line = input("you> ")
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                break

            text = line.strip()
            if not text:
                continue

            if text in ("/exit", "/quit"):
                break

            if text == "/help":
                print(HELP_TEXT)
                continue

            if text == "/memories":
                _print_memories(memory)
                continue

            if text == "/forget" or text.startswith("/forget "):
                _handle_forget(memory, text[len("/forget"):])
                continue

            if text.startswith("/"):
                print(f"Unknown command: {text}. Type /help for commands.")
                continue

            # Otherwise: a chat turn.
            if not has_key:
                print(
                    "Chat is disabled until ANTHROPIC_API_KEY is set. "
                    "Type /help for available commands."
                )
                continue

            if jarvis is None:
                try:
                    # Lazy import via the agent's own lazy anthropic import.
                    from .agent import Jarvis

                    jarvis = Jarvis(memory)
                except Exception as exc:  # noqa: BLE001 - surface, don't crash
                    print(f"Could not start Jarvis: {exc}")
                    continue

            try:
                reply = jarvis.chat(text)
            except Exception as exc:  # noqa: BLE001 - keep the REPL alive
                print(f"Error: {exc}")
                continue

            print("jarvis> " + reply)
    finally:
        memory.close()
