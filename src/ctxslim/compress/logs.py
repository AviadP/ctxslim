"""Log compression: collapse repeated lines, always keep error/warning lines,
window the rest to head + tail."""

import re

IMPORTANT = re.compile(
    r"\b(error|err|warn|warning|fatal|fail|failed|failure|exception|"
    r"traceback|critical|panic|denied|refused|timeout)\b",
    re.IGNORECASE,
)

HEAD_LINES = 40
TAIL_LINES = 20
MAX_IMPORTANT = 200
MIN_RUN_TO_COLLAPSE = 3
MAX_LINE_CHARS = 500


def looks_log_like(text: str) -> bool:
    lines = text.splitlines()
    if len(lines) < 50:
        return False
    return len(text) / len(lines) < 300


def compress_logs(text: str) -> str:
    collapsed = _collapse_runs(text.splitlines())
    return _window(collapsed)


def _normalize(line: str) -> str:
    return re.sub(r"\d+", "#", line)


def _collapse_runs(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        norm = _normalize(lines[i])
        j = i + 1
        while j < len(lines) and _normalize(lines[j]) == norm:
            j += 1
        run = j - i
        if run >= MIN_RUN_TO_COLLAPSE:
            out.append(_clip(lines[i]))
            out.append(f"  [… ×{run - 1} similar lines collapsed …]")
        else:
            out.extend(_clip(line) for line in lines[i:j])
        i = j
    return out


def _window(lines: list[str]) -> str:
    n = len(lines)
    keep = set(range(min(HEAD_LINES, n))) | set(range(max(0, n - TAIL_LINES), n))
    important = [i for i, line in enumerate(lines) if IMPORTANT.search(line)]
    if len(important) > MAX_IMPORTANT:
        important = important[:150] + important[-50:]
    keep |= set(important)

    out: list[str] = []
    prev = -1
    for i in sorted(keep):
        if i != prev + 1:
            out.append(f"  [… {i - prev - 1} lines omitted …]")
        out.append(lines[i])
        prev = i
    return "\n".join(out)


def _clip(line: str) -> str:
    if len(line) > MAX_LINE_CHARS:
        return line[:MAX_LINE_CHARS] + f"… [{len(line) - MAX_LINE_CHARS} more chars]"
    return line
