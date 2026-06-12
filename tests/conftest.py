import json
import random

import pytest


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Point the store at a temp dir so tests never touch ~/.ctxslim."""
    monkeypatch.setenv("CTXSLIM_STORE", str(tmp_path / "store"))


@pytest.fixture
def big_json() -> str:
    items = [
        {"id": i, "name": f"item-{i}", "status": "ok" if i % 7 else "stale"}
        for i in range(500)
    ]
    return json.dumps({"total": 500, "items": items})


@pytest.fixture
def noisy_log() -> str:
    lines = ["2026-06-12 09:14:02 INFO starting ingest batch 4411"]
    for i in range(3000):
        lines.append(f"2026-06-12 09:14:{i % 60:02d} INFO heartbeat ok seq={i}")
    lines.append("2026-06-12 09:14:55 ERROR connection reset by peer (attempt 3/3)")
    lines.append("2026-06-12 09:14:55 ERROR Traceback (most recent call last):")
    for i in range(2000):
        lines.append(f"2026-06-12 09:15:{i % 60:02d} INFO retry queue drained n={i}")
    lines.append("2026-06-12 09:15:01 INFO shutting down")
    return "\n".join(lines)


@pytest.fixture
def generic_dump() -> str:
    # Long lines (avg > 300 chars) so this reads as prose/dump, not as a log.
    rng = random.Random(42)
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"]
    return "\n".join(
        " ".join(rng.choices(words, k=55)) + f" #{i}" for i in range(300)
    )
