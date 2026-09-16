import json
from fastapi.testclient import TestClient
from northline.agent import server
from northline.agent.claude_runner import TurnResult


def test_chat_roundtrip(log_dir, data_dir, monkeypatch):
    seen = {}
    def fake(message, *, system_prompt, mcp_config, session_id=None, model=None, **kw):
        seen.update(cfg=mcp_config, resume=session_id)
        return TurnResult("Hi Thandi", "claude-abc", [], 0.0)
    monkeypatch.setattr(server, "run_turn_fn", fake)
    c = TestClient(server.app)
    r = c.post("/chat", json={"message": "hi", "session_id": None}).json()
    assert r["reply"] == "Hi Thandi" and len(r["session_id"]) == 12 and seen["resume"] is None
    assert seen["cfg"]["mcpServers"]["northline"]["env"]["NORTHLINE_SESSION_ID"] == r["session_id"]
    c.post("/chat", json={"message": "146/92", "session_id": r["session_id"]})
    assert seen["resume"] == "claude-abc"
    assert len(json.loads((log_dir / "transcripts" / f"{r['session_id']}.json").read_text())["messages"]) == 4


def test_index(log_dir):
    assert TestClient(server.app).get("/").status_code == 200
