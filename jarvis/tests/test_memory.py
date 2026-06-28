"""Tests for jarvis.memory.Memory (CRUD + message log).

Runs without pytest installed: plain assert-based test_* functions plus a
__main__ runner. Also pytest-compatible.
"""

import os
import sys
import tempfile

# Make 'import jarvis' work when run directly from the tests directory.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from jarvis.memory import Memory


def _fresh_memory():
    """Return a Memory backed by a fresh temp sqlite file, plus its path."""
    tmpdir = tempfile.mkdtemp(prefix="jarvis_mem_")
    db_path = os.path.join(tmpdir, "nested", "jarvis.db")
    return Memory(db_path), db_path


def test_creates_db_and_parent_dirs():
    mem, db_path = _fresh_memory()
    try:
        assert os.path.exists(db_path), "db file should be created"
        assert os.path.isdir(os.path.dirname(db_path)), "parent dir created"
    finally:
        mem.close()


def test_remember_returns_increasing_ids():
    mem, _ = _fresh_memory()
    try:
        id1 = mem.remember("user likes coffee", kind="preference")
        id2 = mem.remember("user lives in Berlin")
        assert isinstance(id1, int)
        assert isinstance(id2, int)
        assert id2 > id1, "ids should increase"
    finally:
        mem.close()


def test_list_memories_newest_first():
    mem, _ = _fresh_memory()
    try:
        mem.remember("first fact")
        mem.remember("second fact")
        mem.remember("third fact")
        rows = mem.list_memories()
        assert len(rows) == 3
        contents = [r["content"] for r in rows]
        assert contents[0] == "third fact", "newest should be first"
        assert contents[-1] == "first fact"
        # dict shape check
        for r in rows:
            assert set(r.keys()) == {"id", "kind", "content", "created_at"}
    finally:
        mem.close()


def test_list_memories_respects_limit():
    mem, _ = _fresh_memory()
    try:
        for i in range(5):
            mem.remember(f"fact {i}")
        rows = mem.list_memories(limit=2)
        assert len(rows) == 2
    finally:
        mem.close()


def test_recall_keyword_match():
    mem, _ = _fresh_memory()
    try:
        mem.remember("user enjoys mountain hiking")
        mem.remember("user dislikes loud music")
        mem.remember("favorite color is green")
        hits = mem.recall("hiking")
        assert len(hits) == 1
        assert "hiking" in hits[0]["content"]
    finally:
        mem.close()


def test_recall_case_insensitive_and_multiword():
    mem, _ = _fresh_memory()
    try:
        mem.remember("User loves Python programming")
        mem.remember("user owns a Cat")
        # case-insensitive LIKE; either word matches
        hits = mem.recall("PYTHON cat")
        contents = {h["content"] for h in hits}
        assert "User loves Python programming" in contents
        assert "user owns a Cat" in contents
        assert len(hits) == 2
    finally:
        mem.close()


def test_recall_empty_query_falls_back_to_recent():
    mem, _ = _fresh_memory()
    try:
        mem.remember("alpha")
        mem.remember("beta")
        hits = mem.recall("")
        assert len(hits) == 2
        assert hits[0]["content"] == "beta", "newest first on fallback"
    finally:
        mem.close()


def test_recall_no_match_falls_back_to_recent():
    mem, _ = _fresh_memory()
    try:
        mem.remember("alpha")
        mem.remember("beta")
        hits = mem.recall("zzzznotpresent")
        # falls back to most-recent memories rather than empty
        assert len(hits) == 2
        assert hits[0]["content"] == "beta"
    finally:
        mem.close()


def test_recall_respects_limit():
    mem, _ = _fresh_memory()
    try:
        for i in range(5):
            mem.remember(f"keyword item {i}")
        hits = mem.recall("keyword", limit=3)
        assert len(hits) == 3
    finally:
        mem.close()


def test_forget_deletes_and_reports():
    mem, _ = _fresh_memory()
    try:
        mid = mem.remember("temporary fact")
        assert mem.forget(mid) is True
        assert mem.list_memories() == []
        # forgetting again returns False
        assert mem.forget(mid) is False
        # forgetting a nonexistent id returns False
        assert mem.forget(99999) is False
    finally:
        mem.close()


def test_log_message_and_recent_messages_order():
    mem, _ = _fresh_memory()
    try:
        mem.log_message("user", "hello")
        mem.log_message("assistant", "hi there")
        mem.log_message("user", "how are you")
        msgs = mem.recent_messages()
        assert len(msgs) == 3
        # oldest -> newest
        assert msgs[0] == {"role": "user", "content": "hello"}
        assert msgs[1] == {"role": "assistant", "content": "hi there"}
        assert msgs[2] == {"role": "user", "content": "how are you"}
    finally:
        mem.close()


def test_recent_messages_respects_limit_keeps_newest():
    mem, _ = _fresh_memory()
    try:
        for i in range(5):
            mem.log_message("user", f"msg {i}")
        msgs = mem.recent_messages(limit=2)
        assert len(msgs) == 2
        # should keep the two newest, ordered oldest->newest
        assert msgs[0]["content"] == "msg 3"
        assert msgs[1]["content"] == "msg 4"
    finally:
        mem.close()


def test_memory_context_empty_and_populated():
    mem, _ = _fresh_memory()
    try:
        assert mem.memory_context() == "", "no memories -> empty string"
        mem.remember("user prefers dark mode")
        ctx = mem.memory_context()
        assert "Here is what you remember about the user:" in ctx
        assert "user prefers dark mode" in ctx
    finally:
        mem.close()


def _all_tests():
    return [v for k, v in sorted(globals().items()) if k.startswith("test_")]


if __name__ == "__main__":
    for fn in _all_tests():
        fn()
        print(f"ok - {fn.__name__}")
    print("ALL TESTS PASSED")
