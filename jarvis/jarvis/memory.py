"""SQLite-backed persistent memory for Jarvis.

Stores durable memories and a rolling log of conversation messages. All data
lives in a single local SQLite file; nothing leaves the machine.
"""

import datetime
import sqlite3


def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Memory:
    """Long-term memory and message log backed by SQLite."""

    def __init__(self, db_path):
        """Open (or create) the database at ``db_path``.

        ``db_path`` may be a ``str`` or ``pathlib.Path``. The parent directory
        is created if needed, and the required tables are created if absent.
        """
        from pathlib import Path

        path = Path(db_path)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the memories and messages tables if they don't exist."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT,
                content TEXT NOT NULL,
                created_at TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                created_at TEXT
            )
            """
        )
        self.conn.commit()

    # -- Memories ---------------------------------------------------------

    def remember(self, content: str, kind: str = "note") -> int:
        """Save a memory and return its new row id."""
        cur = self.conn.execute(
            "INSERT INTO memories (kind, content, created_at) VALUES (?, ?, ?)",
            (kind, content, _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def recall(self, query: str, limit: int = 5) -> list:
        """Search memories by keyword, newest first.

        Splits ``query`` into words and matches rows whose content contains any
        word (case-insensitive). If the query is empty or nothing matches, falls
        back to the most recent memories.
        """
        words = [w for w in (query or "").split() if w]

        if words:
            clauses = " OR ".join("content LIKE ?" for _ in words)
            params = [f"%{w}%" for w in words]
            rows = self.conn.execute(
                f"""
                SELECT id, kind, content, created_at FROM memories
                WHERE {clauses}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
            if rows:
                return [dict(r) for r in rows]

        # Fallback: most recent memories.
        rows = self.conn.execute(
            """
            SELECT id, kind, content, created_at FROM memories
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_memories(self, limit: int = 50) -> list:
        """Return saved memories, newest first."""
        rows = self.conn.execute(
            """
            SELECT id, kind, content, created_at FROM memories
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def forget(self, memory_id: int) -> bool:
        """Delete a memory by id. Return True if a row was deleted."""
        cur = self.conn.execute(
            "DELETE FROM memories WHERE id = ?", (memory_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    # -- Messages ---------------------------------------------------------

    def log_message(self, role: str, content: str) -> None:
        """Append a message to the conversation log.

        ``role`` is typically "user" or "assistant".
        """
        self.conn.execute(
            "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
            (role, content, _now()),
        )
        self.conn.commit()

    def recent_messages(self, limit: int = 20) -> list:
        """Return the most recent messages, ordered oldest to newest.

        Each item is a dict with ``role`` and ``content`` keys.
        """
        rows = self.conn.execute(
            """
            SELECT role, content FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        # Fetched newest-first; reverse to oldest-first.
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    # -- Prompt injection -------------------------------------------------

    def memory_context(self, limit: int = 20) -> str:
        """Return a human-readable block of recent memories for the prompt.

        Returns "" when there are no memories.
        """
        rows = self.list_memories(limit=limit)
        if not rows:
            return ""

        lines = ["Here is what you remember about the user:"]
        for r in rows:
            lines.append(f"- {r['content']}")
        return "\n".join(lines)

    # -- Lifecycle --------------------------------------------------------

    def close(self) -> None:
        """Close the underlying database connection."""
        self.conn.close()
