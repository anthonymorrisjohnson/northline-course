import json
from northline.agent import transcripts as tr
from northline.agent.claude_runner import TurnResult


def test_record_and_load(log_dir):
    path = tr.record_turn("s1", "hi", TurnResult("hello", "c1", [], 0.01))
    tr.record_turn("s1", "chest tight", TurnResult("call 911", "c1", [{"name": "escalate_to_nurse", "input": {}, "result": "", "is_error": False}], 0.02))
    d = json.loads(path.read_text())
    assert len(d["messages"]) == 4 and d["escalated"] is True and abs(d["cost_usd"] - 0.03) < 1e-9
    assert tr.load_all(log_dir / "transcripts")[0]["session_id"] == "s1"
