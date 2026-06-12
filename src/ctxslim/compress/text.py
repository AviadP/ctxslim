"""Generic text fallback: head + tail with an explicit elision marker."""

HEAD_LINES = 60
TAIL_LINES = 20
HEAD_CHARS = 3000
TAIL_CHARS = 1500
MAX_LINE_CHARS = 500


def compress_text(text: str) -> str:
    lines = text.splitlines()
    if len(lines) > HEAD_LINES + TAIL_LINES + 5:
        head = [_clip(line) for line in lines[:HEAD_LINES]]
        tail = [_clip(line) for line in lines[-TAIL_LINES:]]
        omitted_lines = len(lines) - HEAD_LINES - TAIL_LINES
        omitted_chars = max(
            0,
            len(text)
            - sum(len(line) + 1 for line in lines[:HEAD_LINES])
            - sum(len(line) + 1 for line in lines[-TAIL_LINES:]),
        )
        return (
            "\n".join(head)
            + f"\n[… {omitted_lines:,} lines / ~{omitted_chars:,} chars omitted …]\n"
            + "\n".join(tail)
        )
    # Few lines but huge content (e.g. minified output): char-based elision.
    omitted = len(text) - HEAD_CHARS - TAIL_CHARS
    return (
        text[:HEAD_CHARS]
        + f"\n[… {omitted:,} chars omitted …]\n"
        + text[-TAIL_CHARS:]
    )


def _clip(line: str) -> str:
    if len(line) > MAX_LINE_CHARS:
        return line[:MAX_LINE_CHARS] + f"… [{len(line) - MAX_LINE_CHARS} more chars]"
    return line
