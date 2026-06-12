"""slim — CLI entry point.

Pipe mode:   <command> | slim
Retrieval:   slim get <id> | slim grep <id> <pattern> | slim lines <id> A-B
Maintenance: slim ls | slim clean
Hook:        slim hook   (Claude Code PostToolUse adapter)
"""

import argparse
import re
import sys
import time

from . import hook as hook_mod
from . import store
from .compress import compress, footer

MAX_GREP_MATCHES = 500


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="slim", description=__doc__)
    sub = parser.add_subparsers(dest="cmd")

    p_get = sub.add_parser("get", help="print the full stored original")
    p_get.add_argument("id")

    p_grep = sub.add_parser("grep", help="search a stored original (regex)")
    p_grep.add_argument("id")
    p_grep.add_argument("pattern")

    p_lines = sub.add_parser("lines", help="print a 1-based inclusive line range, e.g. 100-200")
    p_lines.add_argument("id")
    p_lines.add_argument("range")

    sub.add_parser("ls", help="list stored originals")
    sub.add_parser("clean", help="purge entries older than the TTL")
    sub.add_parser("hook", help="Claude Code PostToolUse adapter (reads JSON on stdin)")

    args = parser.parse_args(argv)

    if args.cmd == "hook":
        return hook_mod.main()

    if args.cmd != "clean":
        store.clean()  # opportunistic TTL purge on every non-hook invocation

    try:
        if args.cmd is None:
            return _pipe()
        if args.cmd == "get":
            sys.stdout.write(store.load(args.id))
            return 0
        if args.cmd == "grep":
            return _grep(args.id, args.pattern)
        if args.cmd == "lines":
            return _lines(args.id, args.range)
        if args.cmd == "ls":
            return _ls()
        if args.cmd == "clean":
            removed = store.clean()
            print(f"removed {removed} expired file(s)")
            return 0
    except (ValueError, FileNotFoundError) as exc:
        print(f"slim: {exc}", file=sys.stderr)
        return 1
    return 0


def _pipe() -> int:
    if sys.stdin.isatty():
        print("slim: pipe input expected, e.g.  <command> | slim", file=sys.stderr)
        return 1
    text = sys.stdin.read()
    comp = compress(text)
    if comp is None:
        sys.stdout.write(text)
        return 0
    sid = store.save(text, source="pipe", strategy=comp.strategy)
    sys.stdout.write(comp.body + "\n\n" + footer(comp, sid) + "\n")
    return 0


def _grep(sid: str, pattern: str) -> int:
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        print(f"slim: bad regex: {exc}", file=sys.stderr)
        return 1
    matches = 0
    for n, line in enumerate(store.load(sid).splitlines(), start=1):
        if rx.search(line):
            matches += 1
            if matches > MAX_GREP_MATCHES:
                print(f"[… more matches truncated at {MAX_GREP_MATCHES} …]")
                break
            print(f"{n}: {line}")
    if matches == 0:
        print("(no matches)")
    return 0


def _lines(sid: str, spec: str) -> int:
    m = re.match(r"^(\d+)[-:](\d+)$", spec)
    if not m:
        print(f"slim: bad range '{spec}' (expected A-B, e.g. 100-200)", file=sys.stderr)
        return 1
    start, end = int(m.group(1)), int(m.group(2))
    if start < 1 or end < start:
        print(f"slim: bad range '{spec}'", file=sys.stderr)
        return 1
    all_lines = store.load(sid).splitlines()
    for n in range(start, min(end, len(all_lines)) + 1):
        print(f"{n}: {all_lines[n - 1]}")
    return 0


def _ls() -> int:
    entries = store.list_entries()
    if not entries:
        print("(store is empty)")
        return 0
    now = time.time()
    print(f"{'ID':<10}{'AGE':<10}{'CHARS':>10}  {'TYPE':<6}SOURCE")
    for e in entries:
        age = _human_age(now - e.get("ts", now))
        print(
            f"{e.get('id', '?'):<10}{age:<10}{e.get('chars', 0):>10,}  "
            f"{e.get('strategy', '?'):<6}{e.get('source', '?')}"
        )
    return 0


def _human_age(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    return f"{seconds / 3600:.1f}h"
