import inspect, json
from northline.tools import calllog


def test_wrap_logs_and_preserves(log_dir):
    def add(a: int, b: int = 1) -> dict:
        """Add."""
        return {"status": "ok", "sum": a + b}
    w = calllog.wrap(add, persona="plan", session_id="s1")
    assert w(a=2)["sum"] == 3 and list(inspect.signature(w).parameters) == ["a", "b"] and w.__doc__ == "Add."
    line = json.loads((log_dir / "tool_calls.jsonl").read_text().strip())
    assert line["tool"] == "add" and line["args"] == {"a": 2} and line["persona"] == "plan" and line["session_id"] == "s1"


def test_wrap_records_error(log_dir):
    def bad() -> dict:
        """Bad."""
        return {"status": "error", "message": "nope"}
    calllog.wrap(bad, persona="plan", session_id="s2")()
    assert json.loads((log_dir / "tool_calls.jsonl").read_text().strip())["error"] == "nope"
