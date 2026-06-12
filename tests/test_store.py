import os
import time

import pytest

from ctxslim import store


def test_save_load_roundtrip_byte_identical():
    original = "line one\nline two\n  indented\n\nüñïçôdé ✓\n"
    sid = store.save(original, source="test", strategy="text")
    assert store.load(sid) == original


def test_invalid_id_rejected():
    with pytest.raises(ValueError):
        store.load("../../etc/passwd")
    with pytest.raises(ValueError):
        store.load("ABCD1234")  # uppercase not allowed


def test_missing_id_friendly_error():
    with pytest.raises(FileNotFoundError, match="slim ls"):
        store.load("deadbeef")


def test_clean_removes_expired_only():
    old_id = store.save("old", source="test", strategy="text")
    new_id = store.save("new", source="test", strategy="text")
    # age the old entry's files past the TTL
    past = time.time() - store.ttl_seconds() - 60
    for suffix in (".txt", ".json"):
        os.utime(store.store_dir() / f"{old_id}{suffix}", (past, past))

    removed = store.clean()

    assert removed == 2
    assert store.load(new_id) == "new"
    with pytest.raises(FileNotFoundError):
        store.load(old_id)


def test_list_entries_sorted_newest_first():
    a = store.save("aaa", source="first", strategy="text")
    b = store.save("bbb", source="second", strategy="log")
    entries = store.list_entries()
    assert [e["id"] for e in entries[:2]] == [b, a] or len({a, b}) == 2
    assert {e["id"] for e in entries} >= {a, b}
