"""Tests for the Jarvis manual tool-use loop using a FAKE client.

No network, no 'anthropic' package required: a fake client is injected into
Jarvis. The fake returns a tool_use response first, then an end_turn response.

Runs without pytest installed: plain assert-based test_* functions plus a
__main__ runner. Also pytest-compatible.
"""

import os
import sys
import tempfile
from types import SimpleNamespace

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from jarvis.agent import Jarvis
from jarvis.memory import Memory


def _fresh_memory():
    tmpdir = tempfile.mkdtemp(prefix="jarvis_agent_")
    return Memory(os.path.join(tmpdir, "jarvis.db"))


def _text_block(text):
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(name, tool_input, block_id="tool_1"):
    return SimpleNamespace(
        type="tool_use", name=name, input=tool_input, id=block_id
    )


def _response(content, stop_reason):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


class _Messages:
    """Stub for client.messages with a scripted .create()."""

    def __init__(self, owner):
        self._owner = owner

    def create(self, **kwargs):
        self._owner.calls.append(kwargs)
        idx = self._owner._next
        self._owner._next += 1
        return self._owner.scripted[idx]


class FakeClient:
    """Returns a queued sequence of responses; records each create() call."""

    def __init__(self, scripted):
        self.scripted = scripted
        self._next = 0
        self.calls = []
        self.messages = _Messages(self)


def test_tool_loop_dispatches_then_returns_text():
    mem = _fresh_memory()
    try:
        scripted = [
            # 1st turn: model asks to call 'remember'
            _response(
                [
                    _tool_use_block(
                        "remember",
                        {"content": "user's name is Jason", "kind": "fact"},
                    )
                ],
                stop_reason="tool_use",
            ),
            # 2nd turn: model produces the final answer
            _response(
                [_text_block("Got it — I'll remember that, Jason.")],
                stop_reason="end_turn",
            ),
        ]
        client = FakeClient(scripted)
        jarvis = Jarvis(mem, client=client)

        reply = jarvis.chat("My name is Jason, please remember it.")

        # Final text returned
        assert reply == "Got it — I'll remember that, Jason."

        # The tool actually ran: a memory was saved to the real Memory.
        rows = mem.list_memories()
        assert len(rows) == 1
        assert rows[0]["content"] == "user's name is Jason"
        assert rows[0]["kind"] == "fact"

        # The model was called twice (tool turn + final turn).
        assert len(client.calls) == 2

        # The second call must include the tool_result echoed back as a user msg.
        second_msgs = client.calls[1]["messages"]
        assistant_turn = second_msgs[-2]
        tool_result_turn = second_msgs[-1]
        assert assistant_turn["role"] == "assistant"
        assert tool_result_turn["role"] == "user"
        block = tool_result_turn["content"][0]
        assert block["type"] == "tool_result"
        assert block["tool_use_id"] == "tool_1"
        assert "id=" in block["content"]

        # The final assistant text was logged to memory.
        logged = mem.recent_messages()
        assert logged[0] == {
            "role": "user",
            "content": "My name is Jason, please remember it.",
        }
        assert logged[-1] == {
            "role": "assistant",
            "content": "Got it — I'll remember that, Jason.",
        }
    finally:
        mem.close()


def test_chat_logs_user_before_calling_model():
    """The first create() call should already include the user turn."""
    mem = _fresh_memory()
    try:
        scripted = [
            _response([_text_block("hello back")], stop_reason="end_turn"),
        ]
        client = FakeClient(scripted)
        jarvis = Jarvis(mem, client=client)

        reply = jarvis.chat("hello there")
        assert reply == "hello back"

        first_msgs = client.calls[0]["messages"]
        assert first_msgs[-1] == {"role": "user", "content": "hello there"}
        # No tool round-trip needed.
        assert len(client.calls) == 1
    finally:
        mem.close()


def test_system_prompt_includes_memory_context():
    mem = _fresh_memory()
    try:
        mem.remember("user prefers metric units")
        scripted = [
            _response([_text_block("ok")], stop_reason="end_turn"),
        ]
        client = FakeClient(scripted)
        jarvis = Jarvis(mem, client=client)
        jarvis.chat("hi")

        system = client.calls[0]["system"]
        assert "Jarvis" in system
        assert "user prefers metric units" in system
        # tools were passed through
        assert client.calls[0]["tools"]
    finally:
        mem.close()


def test_multiple_tool_iterations():
    """Two sequential tool_use rounds before the final text reply."""
    mem = _fresh_memory()
    try:
        scripted = [
            _response(
                [_tool_use_block("remember", {"content": "fact one"}, "t1")],
                stop_reason="tool_use",
            ),
            _response(
                [_tool_use_block("remember", {"content": "fact two"}, "t2")],
                stop_reason="tool_use",
            ),
            _response([_text_block("done")], stop_reason="end_turn"),
        ]
        client = FakeClient(scripted)
        jarvis = Jarvis(mem, client=client)

        reply = jarvis.chat("remember two things")
        assert reply == "done"
        assert len(client.calls) == 3
        contents = sorted(r["content"] for r in mem.list_memories())
        assert contents == ["fact one", "fact two"]
    finally:
        mem.close()


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_")]


if __name__ == "__main__":
    for fn in _all_tests():
        fn()
        print(f"ok - {fn.__name__}")
    print("ALL TESTS PASSED")
