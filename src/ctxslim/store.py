"""Local store for original (pre-compression) outputs, with TTL cleanup."""

import hashlib
import json
import os
import re
import time
from pathlib import Path

DEFAULT_TTL_SECONDS = 24 * 3600
_ID_RE = re.compile(r"^[0-9a-f]{8}$")


def store_dir() -> Path:
    d = Path(os.environ.get("CTXSLIM_STORE", "~/.ctxslim/store")).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def ttl_seconds() -> int:
    try:
        return int(os.environ.get("CTXSLIM_TTL", DEFAULT_TTL_SECONDS))
    except ValueError:
        return DEFAULT_TTL_SECONDS


def save(text: str, source: str, strategy: str) -> str:
    sid = hashlib.sha1(f"{time.time_ns()}:{len(text)}".encode()).hexdigest()[:8]
    d = store_dir()
    (d / f"{sid}.txt").write_text(text, encoding="utf-8")
    meta = {
        "id": sid,
        "ts": time.time(),
        "source": source[:120],
        "chars": len(text),
        "strategy": strategy,
    }
    (d / f"{sid}.json").write_text(json.dumps(meta), encoding="utf-8")
    return sid


def load(sid: str) -> str:
    _validate(sid)
    path = store_dir() / f"{sid}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"no stored output with id '{sid}' (expired or never existed; see `slim ls`)"
        )
    return path.read_text(encoding="utf-8")


def list_entries() -> list[dict]:
    entries = []
    for meta_path in store_dir().glob("*.json"):
        try:
            entries.append(json.loads(meta_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return sorted(entries, key=lambda e: e.get("ts", 0), reverse=True)


def clean(ttl: int | None = None) -> int:
    """Delete entries older than the TTL. Returns number of files removed."""
    ttl = ttl_seconds() if ttl is None else ttl
    now = time.time()
    removed = 0
    for path in store_dir().iterdir():
        try:
            if now - path.stat().st_mtime > ttl:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def _validate(sid: str) -> None:
    if not _ID_RE.match(sid):
        raise ValueError(f"invalid id '{sid}' (expected 8 hex chars)")
