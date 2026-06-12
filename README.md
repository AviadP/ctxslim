# ctxslim

Safe, deterministic, **reversible** context compression for Claude Code tool outputs.

When a Bash command or MCP tool returns a huge dump (logs, JSON, file listings), a
PostToolUse hook replaces it in-context with a compact digest — repeated lines
collapsed with counts, long JSON arrays sampled with a schema summary, errors and
tracebacks always kept verbatim — plus a footer telling Claude (and you) how to
retrieve the full original from a local store.

Inspired by [Headroom](https://github.com/chopratejas/headroom), minus everything
heavy or risky: no ML models, no network access ever, no proxy in your request path.
Python stdlib only — zero dependencies.

## Safety properties

- **Reversible** — the original is saved to `~/.ctxslim/store/` *before* compression;
  `slim get <id>` returns it byte-identical. TTL cleanup (default 24h).
- **Fail-open** — any error in the hook → exit 0 with no output → Claude Code uses
  the untouched original. The hook can never break a session.
- **Threshold-gated** — output under 4,000 chars (or where compression saves <20%)
  passes through byte-identical.
- **Error-preserving** — lines matching error/warn/traceback patterns are never elided.
- **No self-interference** — output of `slim` retrieval commands is never re-compressed.

## Install

Requires Python ≥ 3.10. No dependencies.

```bash
git clone https://github.com/AviadP/ctxslim.git ~/ctxslim
cd ~/ctxslim
python3 -m venv .venv          # use python3.11+ if your default python3 is older
.venv/bin/pip install -e .
```

## Enable the Claude Code hook

Add to `~/.claude/settings.json` (or a project's `.claude/settings.json` to scope
it). Use the **absolute** venv path so the hook works regardless of PATH —
replace `/ABSOLUTE/PATH/TO` with where you cloned it:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "/ABSOLUTE/PATH/TO/ctxslim/.venv/bin/slim hook", "timeout": 10 }]
      },
      {
        "matcher": "mcp__.*",
        "hooks": [{ "type": "command", "command": "/ABSOLUTE/PATH/TO/ctxslim/.venv/bin/slim hook", "timeout": 10 }]
      }
    ]
  }
}
```

Hooks load at session start, so restart your Claude Code session after adding them.
Disable any time by removing those entries.

**How it plays with Claude Code's own limits:** Claude Code truncates Bash output
at ~30k chars *before* hooks run, so for Bash the hook covers the 4k–30k range and
turns blind truncation into structured, recoverable elision. MCP tool outputs are
passed to the hook in full — that's where the biggest savings live.

## CLI

```bash
<command> | slim              # pipe mode: compress + store, print digest
slim get <id>                 # full original, byte-identical
slim grep <id> <regex>        # search the original without re-dumping it
slim lines <id> 100-200       # 1-based inclusive line range
slim ls                       # stored originals (id, age, size, source)
slim clean                    # purge expired entries (also runs opportunistically)
```

Example digest footer appended to every compressed output:

```
[ctxslim: 154,670 → 649 chars (100% smaller). Full output: slim get 11b47079 |
 search: slim grep 11b47079 <pattern> | range: slim lines 11b47079 <start>-<end>]
```

## Configuration (env vars)

| Variable | Default | Meaning |
|---|---|---|
| `CTXSLIM_THRESHOLD` | `4000` | chars below which output passes through untouched |
| `CTXSLIM_TTL` | `86400` | seconds before stored originals are purged |
| `CTXSLIM_STORE` | `~/.ctxslim/store` | where originals are kept |

## Compression strategies

| Input | Strategy | What happens |
|---|---|---|
| Valid JSON | `json` | arrays > 8 items keep first 5 + last 2 + `"… N more items, keys: […]"`; strings > 400 chars clipped; structure intact |
| Many short lines | `log` | consecutive similar lines (digits normalized) collapsed to `[… ×N similar lines collapsed …]`; error/warn/traceback lines always kept; head 40 + tail 20 window |
| Everything else | `text` | head 60 + tail 20 lines (or char-based for minified blobs) with `[… N lines omitted …]` |

## Non-goals (v1)

No ML/semantic compression, no LLM calls, no proxy mode, no secret redaction,
no conversation-history compaction (Claude Code already does that).

## Tests

```bash
.venv/bin/python -m pytest
```
