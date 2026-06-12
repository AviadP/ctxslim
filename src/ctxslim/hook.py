"""Claude Code PostToolUse adapter.

Reads the hook payload on stdin; if the tool response carries a large text
body, emits `hookSpecificOutput.updatedToolOutput` JSON with the compressed
version. Fail-open: on any error, exit 0 with no output so Claude Code uses
the original response untouched.
"""

import json
import re
import sys

from . import store
from .compress import compress, footer

# Never compress the output of slim's own retrieval commands, or retrieval
# would be re-compressed and the original would stay unreachable.
_SLIM_CMD = re.compile(r"(^|[;&|]\s*|\s)(slim|python3? -m ctxslim)\s")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        result = process(payload)
        if result is not None:
            json.dump(result, sys.stdout)
    except Exception:
        pass
    return 0


def process(payload: dict) -> dict | None:
    if _is_slim_invocation(payload):
        return None
    updated = _transform(payload.get("tool_response"), _source(payload))
    if updated is None:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": updated,
        }
    }


def _is_slim_invocation(payload: dict) -> bool:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str) and _SLIM_CMD.search(command):
            return True
    return False


def _transform(response, source: str):
    if isinstance(response, str):
        return _compress_str(response, source)
    if isinstance(response, dict):
        for key in ("stdout", "output", "text"):
            value = response.get(key)
            if isinstance(value, str):
                new = _compress_str(value, source)
                if new is not None:
                    updated = dict(response)
                    updated[key] = new
                    return updated
        return None
    if isinstance(response, list):
        changed = False
        blocks = []
        for block in response:
            if (
                isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            ):
                new = _compress_str(block["text"], source)
                if new is not None:
                    block = {**block, "text": new}
                    changed = True
            blocks.append(block)
        return blocks if changed else None
    return None


def _compress_str(text: str, source: str) -> str | None:
    comp = compress(text)
    if comp is None:
        return None
    sid = store.save(text, source=source, strategy=comp.strategy)
    return comp.body + "\n\n" + footer(comp, sid)


def _source(payload: dict) -> str:
    name = payload.get("tool_name", "?")
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            return f"{name}: {command[:100]}"
    return str(name)
