"""Core conversation engine for Jarvis.

Implements a manual tool-use loop using the Anthropic Python SDK (Claude
Opus 4.8). The :class:`Jarvis` class logs conversation turns, injects
remembered context into the system prompt, and drives the model through any
tool calls until it produces a final text reply.
"""

from . import config
from . import tools


class Jarvis:
    """Stateful chat agent backed by a :class:`~jarvis.memory.Memory`."""

    # Hard cap on tool-use iterations to avoid an infinite tool loop.
    MAX_TOOL_ITERATIONS = 10

    def __init__(
        self,
        memory,
        client=None,
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        max_history=20,
    ):
        self.memory = memory
        self.model = model
        self.max_tokens = max_tokens
        self.max_history = max_history

        if client is None:
            # Lazy import so unit tests can inject a fake client without the
            # 'anthropic' package being installed.
            import anthropic

            client = anthropic.Anthropic()
        self.client = client

    def _build_system(self) -> str:
        """Combine the base persona with any remembered context."""
        ctx = self.memory.memory_context()
        if ctx:
            return config.BASE_SYSTEM_PROMPT + "\n\n" + ctx
        return config.BASE_SYSTEM_PROMPT

    def chat(self, user_text: str) -> str:
        """Process one user turn and return Jarvis's final text reply."""
        self.memory.log_message("user", user_text)

        system = self._build_system()
        # recent_messages() already ends with the just-logged user turn.
        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in self.memory.recent_messages(self.max_history)
        ]

        final_text = self._run_tool_loop(system, messages)

        self.memory.log_message("assistant", final_text)
        return final_text

    def _run_tool_loop(self, system: str, messages: list) -> str:
        """Drive the manual tool-use loop and return the concatenated text."""
        for _ in range(self.MAX_TOOL_ITERATIONS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=messages,
                tools=tools.TOOLS,
            )

            if response.stop_reason != "tool_use":
                return self._collect_text(response.content)

            # Echo the assistant turn (including tool_use blocks) back into history.
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    result = tools.dispatch(self.memory, block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            messages.append({"role": "user", "content": tool_results})

        # Hit the iteration cap; make a final non-tool request would still loop,
        # so return whatever text the last response carried.
        return self._collect_text(response.content)

    @staticmethod
    def _collect_text(content) -> str:
        """Concatenate the text from all 'text' blocks in a response."""
        parts = [
            block.text
            for block in content
            if getattr(block, "type", None) == "text"
        ]
        return "".join(parts)
