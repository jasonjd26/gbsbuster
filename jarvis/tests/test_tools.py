"""Tests for jarvis.tools.dispatch against a real Memory on a tmp db.

Runs without pytest installed: plain assert-based test_* functions plus a
__main__ runner. Also pytest-compatible.
"""

import os
import re
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from jarvis import tools
from jarvis.memory import Memory


def _fresh_memory():
    tmpdir = tempfile.mkdtemp(prefix="jarvis_tools_")
    return Memory(os.path.join(tmpdir, "jarvis.db"))


def test_tools_schema_shape():
    names = {t["name"] for t in tools.TOOLS}
    assert names == {
        "remember",
        "recall",
        "list_memories",
        "forget",
        "get_datetime",
    }
    for t in tools.TOOLS:
        assert "description" in t
        schema = t["input_schema"]
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert "properties" in schema
        assert "required" in schema


def test_dispatch_remember_saves_and_returns_id():
    mem = _fresh_memory()
    try:
        out = tools.dispatch(mem, "remember", {"content": "user likes tea"})
        m = re.search(r"id=(\d+)", out)
        assert m, f"expected an id in result, got: {out!r}"
        new_id = int(m.group(1))
        # verify it really persisted
        rows = mem.list_memories()
        assert len(rows) == 1
        assert rows[0]["content"] == "user likes tea"
        assert rows[0]["id"] == new_id
    finally:
        mem.close()


def test_dispatch_remember_with_kind():
    mem = _fresh_memory()
    try:
        tools.dispatch(
            mem, "remember", {"content": "loves jazz", "kind": "preference"}
        )
        rows = mem.list_memories()
        assert rows[0]["kind"] == "preference"
    finally:
        mem.close()


def test_dispatch_remember_missing_content_errors():
    mem = _fresh_memory()
    try:
        out = tools.dispatch(mem, "remember", {})
        assert "Error" in out
        assert mem.list_memories() == []
    finally:
        mem.close()


def test_dispatch_recall_finds_match():
    mem = _fresh_memory()
    try:
        mem.remember("user works as an astronomer")
        out = tools.dispatch(mem, "recall", {"query": "astronomer"})
        assert "astronomer" in out
        assert "No memories found" not in out
    finally:
        mem.close()


def test_dispatch_recall_no_memories_at_all():
    mem = _fresh_memory()
    try:
        out = tools.dispatch(mem, "recall", {"query": "anything"})
        assert out == "No memories found."
    finally:
        mem.close()


def test_dispatch_list_memories():
    mem = _fresh_memory()
    try:
        mem.remember("fact A")
        mem.remember("fact B")
        out = tools.dispatch(mem, "list_memories", {})
        assert "fact A" in out
        assert "fact B" in out
    finally:
        mem.close()


def test_dispatch_list_memories_empty():
    mem = _fresh_memory()
    try:
        out = tools.dispatch(mem, "list_memories", {})
        assert out == "No memories found."
    finally:
        mem.close()


def test_dispatch_forget_success_and_missing():
    mem = _fresh_memory()
    try:
        mid = mem.remember("disposable")
        out = tools.dispatch(mem, "forget", {"memory_id": mid})
        assert str(mid) in out
        assert mem.list_memories() == []
        # forgetting again -> not found
        out2 = tools.dispatch(mem, "forget", {"memory_id": mid})
        assert "No memory found" in out2
    finally:
        mem.close()


def test_dispatch_forget_missing_arg():
    mem = _fresh_memory()
    try:
        out = tools.dispatch(mem, "forget", {})
        assert "Error" in out
    finally:
        mem.close()


def test_dispatch_get_datetime():
    mem = _fresh_memory()
    try:
        out = tools.dispatch(mem, "get_datetime", {})
        # ISO-ish "YYYY-MM-DD HH:MM:SS..." with a space separator
        assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", out), out
    finally:
        mem.close()


def test_dispatch_unknown_tool():
    mem = _fresh_memory()
    try:
        out = tools.dispatch(mem, "no_such_tool", {})
        assert "Error" in out
        assert "no_such_tool" in out
    finally:
        mem.close()


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_")]


if __name__ == "__main__":
    for fn in _all_tests():
        fn()
        print(f"ok - {fn.__name__}")
    print("ALL TESTS PASSED")
