"""JSON compression: sample long arrays, clip long strings, keep structure intact."""

import json

HEAD_ITEMS = 5
TAIL_ITEMS = 2
MAX_STR = 400
MAX_MARKER_KEYS = 12


def compress_json_text(obj) -> str:
    return json.dumps(_walk(obj), indent=1, ensure_ascii=False)


def _walk(node):
    if isinstance(node, list):
        if len(node) > HEAD_ITEMS + TAIL_ITEMS + 1:
            elided = node[HEAD_ITEMS : len(node) - TAIL_ITEMS]
            head = [_walk(x) for x in node[:HEAD_ITEMS]]
            tail = [_walk(x) for x in node[-TAIL_ITEMS:]]
            return head + [_marker(elided)] + tail
        return [_walk(x) for x in node]
    if isinstance(node, dict):
        return {k: _walk(v) for k, v in node.items()}
    if isinstance(node, str) and len(node) > MAX_STR:
        return node[:MAX_STR] + f"… [{len(node) - MAX_STR} more chars]"
    return node


def _marker(elided: list) -> str:
    keys = sorted({k for item in elided if isinstance(item, dict) for k in item})
    if keys:
        shown = ", ".join(keys[:MAX_MARKER_KEYS])
        if len(keys) > MAX_MARKER_KEYS:
            shown += ", …"
        return f"… {len(elided)} more items, keys: [{shown}]"
    return f"… {len(elided)} more items"
