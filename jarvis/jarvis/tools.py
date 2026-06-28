"""Tool schemas and dispatcher for Jarvis.

Defines the Claude tool definitions (JSON Schema) and a `dispatch` function
that executes a named tool against a :class:`~jarvis.memory.Memory` instance.
"""

import datetime


# Claude tool definitions. Each entry is a dict with name/description/input_schema,
# where input_schema is a JSON Schema object with additionalProperties disabled.
TOOLS = [
    {
        "name": "remember",
        "description": (
            "Save a durable fact, preference, or piece of context about the user "
            "to long-term memory so it can be recalled in future conversations. "
            "Use this proactively whenever the user shares something worth keeping."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The fact or context to remember.",
                },
                "kind": {
                    "type": "string",
                    "description": (
                        "Optional category for the memory, e.g. 'preference', "
                        "'fact', or 'note'. Defaults to 'note'."
                    ),
                },
            },
            "required": ["content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "recall",
        "description": (
            "Search long-term memory for saved facts and context relevant to a "
            "query. Use this before answering when remembered information may help."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords to search remembered content for.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return. Defaults to 5.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_memories",
        "description": "List the most recently saved memories, newest first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to list. Defaults to 50.",
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "forget",
        "description": "Delete a saved memory by its numeric id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "integer",
                    "description": "The id of the memory to delete.",
                },
            },
            "required": ["memory_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_datetime",
        "description": "Get the current local date and time.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
]


def _format_memory(mem: dict) -> str:
    """Render a single memory dict as a readable one-line string."""
    kind = mem.get("kind") or "note"
    return f"[{mem['id']}] ({kind}) {mem['content']}"


def dispatch(memory, name: str, tool_input: dict) -> str:
    """Execute the named tool against ``memory`` and return a string result.

    Unknown tool names return an error string rather than raising, so the
    agent loop can surface the problem back to the model as a tool result.
    """
    tool_input = tool_input or {}

    if name == "remember":
        content = tool_input.get("content")
        if not content:
            return "Error: 'content' is required to remember something."
        kind = tool_input.get("kind", "note") or "note"
        new_id = memory.remember(content, kind=kind)
        return f"Saved (id={new_id})."

    if name == "recall":
        query = tool_input.get("query", "") or ""
        limit = tool_input.get("limit", 5)
        results = memory.recall(query, limit=limit)
        if not results:
            return "No memories found."
        return "\n".join(_format_memory(m) for m in results)

    if name == "list_memories":
        limit = tool_input.get("limit", 50)
        results = memory.list_memories(limit=limit)
        if not results:
            return "No memories found."
        return "\n".join(_format_memory(m) for m in results)

    if name == "forget":
        memory_id = tool_input.get("memory_id")
        if memory_id is None:
            return "Error: 'memory_id' is required to forget a memory."
        try:
            memory_id = int(memory_id)
        except (TypeError, ValueError):
            return f"Error: invalid memory_id {memory_id!r}."
        if memory.forget(memory_id):
            return f"Forgot memory id={memory_id}."
        return f"No memory found with id={memory_id}."

    if name == "get_datetime":
        return datetime.datetime.now().isoformat(sep=" ")

    return f"Error: unknown tool '{name}'."
