import json, subprocess, threading, pytest
from types import SimpleNamespace
from northline.pm import claude_json as cj
S = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}


def test_ask_json():
    def fake(cmd, **kw):
        assert "--json-schema" in cmd and cmd[cmd.index("--tools") + 1] == ""
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": 3}}), returncode=0, stderr="")
    assert cj.ask_json("p", S, runner=fake) == {"x": 3}


def test_ask_json_error():
    def fake(cmd, **kw):
        return SimpleNamespace(stdout=json.dumps({"is_error": True, "result": "rate limited"}), returncode=0, stderr="")
    with pytest.raises(RuntimeError, match="rate limited"):
        cj.ask_json("p", S, runner=fake)


def test_many_in_order():
    def fake(cmd, **kw):
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": int(cmd[2])}}), returncode=0, stderr="")
    assert [o["x"] for o in cj.ask_json_many([(str(i), S) for i in range(6)], workers=3, runner=fake)] == list(range(6))


def test_ask_json_non_json_output():
    def fake(cmd, **kw):
        return SimpleNamespace(stdout="not json", returncode=0, stderr="")
    with pytest.raises(RuntimeError, match="claude returned non-JSON output"):
        cj.ask_json("p", S, runner=fake)


def test_many_retries_once():
    calls = []
    lock = threading.Lock()

    def fake(cmd, **kw):
        with lock:
            calls.append(cmd[2])
            n = calls.count(cmd[2])
        if cmd[2] == "2" and n == 1:
            return SimpleNamespace(stdout=json.dumps({"is_error": True, "result": "boom"}), returncode=0, stderr="")
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": int(cmd[2])}}), returncode=0, stderr="")

    results = cj.ask_json_many([(str(i), S) for i in range(6)], workers=3, runner=fake)
    assert [o["x"] for o in results] == list(range(6))
    assert len(calls) == 7


def test_many_raises_after_retries():
    def fake(cmd, **kw):
        if cmd[2] == "2":
            return SimpleNamespace(stdout=json.dumps({"is_error": True, "result": "boom"}), returncode=0, stderr="")
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": int(cmd[2])}}), returncode=0, stderr="")
    with pytest.raises(RuntimeError, match="boom"):
        cj.ask_json_many([(str(i), S) for i in range(6)], workers=3, runner=fake)


def test_ask_json_timeout_is_runtime_error():
    def fake(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 300)
    with pytest.raises(RuntimeError, match="claude timed out after 300 s"):
        cj.ask_json("p", S, runner=fake)


def test_many_retries_a_timeout():
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd[2])
        if cmd[2] == "0" and calls.count("0") == 1:
            raise subprocess.TimeoutExpired(cmd, 300)
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": int(cmd[2])}}), returncode=0, stderr="")

    assert [o["x"] for o in cj.ask_json_many([("0", S)], workers=1, runner=fake)] == [0]
    assert len(calls) == 2


def test_command_starts_with_the_resolved_binary():
    seen = {}

    def fake(cmd, **kw):
        seen["cmd"] = cmd
        return SimpleNamespace(stdout=json.dumps({"is_error": False, "structured_output": {"x": 1}}), returncode=0, stderr="")

    cj.ask_json("p", S, runner=fake)
    assert seen["cmd"][0].endswith("claude") and seen["cmd"][0] == cj.CLAUDE


def test_missing_binary_raises_at_call_time(monkeypatch):
    monkeypatch.setattr(cj, "CLAUDE", None)
    with pytest.raises(RuntimeError, match="not on PATH"):
        cj.ask_json("p", S, runner=lambda *a, **k: None)
