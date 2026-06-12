from ctxslim.compress import MIN_SAVINGS, Compressed, compress, footer


def test_below_threshold_passes_through():
    assert compress("short output") is None


def test_threshold_env_override(monkeypatch):
    monkeypatch.setenv("CTXSLIM_THRESHOLD", "100")
    text = "x\n" * 2000
    assert compress(text) is not None


def test_json_arrays_are_sampled(big_json):
    comp = compress(big_json)
    assert comp is not None and comp.strategy == "json"
    assert len(comp.body) < len(big_json) * (1 - MIN_SAVINGS)
    # head and tail items survive, elided middle is summarized with keys
    assert '"item-0"' in comp.body
    assert '"item-499"' in comp.body
    assert "493 more items" in comp.body
    assert "id, name, status" in comp.body


def test_logs_keep_errors_and_collapse_repeats(noisy_log):
    comp = compress(noisy_log)
    assert comp is not None and comp.strategy == "log"
    assert len(comp.body) < len(noisy_log) * 0.2
    assert "ERROR connection reset by peer" in comp.body
    assert "ERROR Traceback" in comp.body
    assert "shutting down" in comp.body  # tail preserved
    assert "collapsed" in comp.body or "omitted" in comp.body


def test_generic_text_head_tail(generic_dump):
    comp = compress(generic_dump)
    assert comp is not None and comp.strategy == "text"
    first_line = generic_dump.splitlines()[0]
    last_line = generic_dump.splitlines()[-1]
    assert first_line in comp.body
    assert last_line in comp.body
    assert "omitted" in comp.body


def test_incompressible_passes_through():
    # Just over threshold, single line: head+tail elision would not save
    # enough, so it must pass through rather than grow or barely shrink.
    import random

    rng = random.Random(1)
    text = "".join(rng.choice("abcdefghij") for _ in range(4500))
    assert compress(text) is None


def test_footer_format(big_json):
    comp = compress(big_json)
    f = footer(comp, "abcd1234")
    assert "slim get abcd1234" in f
    assert "slim grep abcd1234" in f
    assert "slim lines abcd1234" in f
    assert "% smaller" in f
