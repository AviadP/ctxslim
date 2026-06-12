import json
import os
import subprocess
import sys
from pathlib import Path

from ctxslim import store
from ctxslim.hook import process

SRC = Path(__file__).resolve().parent.parent / "src"


def _bash_payload(stdout: str, command: str = "cat big.log") -> dict:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"stdout": stdout, "stderr": ""},
    }


def test_bash_stdout_compressed(noisy_log):
    result = process(_bash_payload(noisy_log))
    assert result is not None
    out = result["hookSpecificOutput"]
    assert out["hookEventName"] == "PostToolUse"
    updated = out["updatedToolOutput"]
    assert isinstance(updated, dict)  # shape mirrors the original response
    assert updated["stderr"] == ""
    assert "slim get " in updated["stdout"]
    assert len(updated["stdout"]) < len(noisy_log) * 0.5


def test_original_retrievable_after_hook(noisy_log):
    result = process(_bash_payload(noisy_log))
    sid = result["hookSpecificOutput"]["updatedToolOutput"]["stdout"].split(
        "slim get "
    )[1][:8]
    assert store.load(sid) == noisy_log


def test_small_output_untouched():
    assert process(_bash_payload("all good\n")) is None


def test_slim_commands_never_recompressed(noisy_log):
    for cmd in ("slim get abcd1234", "slim grep abcd1234 error", "python3 -m ctxslim get abcd1234"):
        assert process(_bash_payload(noisy_log, command=cmd)) is None


def test_string_response(generic_dump):
    payload = {"tool_name": "WebFetch", "tool_input": {}, "tool_response": generic_dump}
    result = process(payload)
    updated = result["hookSpecificOutput"]["updatedToolOutput"]
    assert isinstance(updated, str)
    assert "slim get " in updated


def test_mcp_content_blocks(big_json):
    payload = {
        "tool_name": "mcp__db__query",
        "tool_input": {"sql": "select *"},
        "tool_response": [{"type": "text", "text": big_json}],
    }
    result = process(payload)
    blocks = result["hookSpecificOutput"]["updatedToolOutput"]
    assert isinstance(blocks, list) and blocks[0]["type"] == "text"
    assert "slim get " in blocks[0]["text"]


def test_unknown_shapes_ignored():
    assert process({"tool_name": "X", "tool_response": 42}) is None
    assert process({"tool_name": "X", "tool_response": {"weird": True}}) is None
    assert process({}) is None


def test_fail_open_on_garbage_stdin(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(SRC), "CTXSLIM_STORE": str(tmp_path / "s")}
    proc = subprocess.run(
        [sys.executable, "-m", "ctxslim", "hook"],
        input="this is not json {{{",
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_hook_output_is_valid_json(noisy_log, tmp_path):
    env = {**os.environ, "PYTHONPATH": str(SRC), "CTXSLIM_STORE": str(tmp_path / "s")}
    proc = subprocess.run(
        [sys.executable, "-m", "ctxslim", "hook"],
        input=json.dumps(_bash_payload(noisy_log)),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 0
    parsed = json.loads(proc.stdout)
    assert "updatedToolOutput" in parsed["hookSpecificOutput"]
