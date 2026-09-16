import json, threading, pytest
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
