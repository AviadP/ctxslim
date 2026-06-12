"""Content-type detection, dispatch, threshold gating, and footer rendering."""

import json
import os
from dataclasses import dataclass

from . import jsonlike, logs
from . import text as textmod

DEFAULT_THRESHOLD = 4000
MIN_SAVINGS = 0.20  # skip compression unless it saves at least this fraction


@dataclass
class Compressed:
    body: str
    strategy: str
    original_chars: int


def threshold() -> int:
    try:
        return int(os.environ.get("CTXSLIM_THRESHOLD", DEFAULT_THRESHOLD))
    except ValueError:
        return DEFAULT_THRESHOLD


def compress(text: str) -> Compressed | None:
    """Compress text, or return None if it should pass through untouched."""
    if len(text) <= threshold():
        return None
    body, strategy = _dispatch(text)
    if len(body) > len(text) * (1 - MIN_SAVINGS):
        return None
    return Compressed(body=body, strategy=strategy, original_chars=len(text))


def footer(comp: Compressed, store_id: str) -> str:
    pct = 100 - round(100 * len(comp.body) / comp.original_chars)
    return (
        f"[ctxslim: {comp.original_chars:,} → {len(comp.body):,} chars ({pct}% smaller). "
        f"Full output: slim get {store_id} | search: slim grep {store_id} <pattern> | "
        f"range: slim lines {store_id} <start>-<end>]"
    )


def _dispatch(text: str) -> tuple[str, str]:
    obj = _try_json(text)
    if obj is not None:
        return jsonlike.compress_json_text(obj), "json"
    if logs.looks_log_like(text):
        return logs.compress_logs(text), "log"
    return textmod.compress_text(text), "text"


def _try_json(text: str):
    stripped = text.strip()
    if not stripped or stripped[0] not in "{[":
        return None
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, RecursionError):
        return None
