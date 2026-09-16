import json
from fastapi.testclient import TestClient
from northline.agent import server


def test_api_sim_and_dashboard(log_dir, data_dir):
    c = TestClient(server.app)
    d = c.get("/api/sim").json()
    assert "last_quarter" in d["summary"] and len(d["weekly"]["history"]) == 39
    assert c.get("/dashboard").status_code == 200


def test_api_live_counts(log_dir, data_dir):
    (log_dir / "queue.jsonl").write_text(json.dumps({"id": "esc-1", "answered_at": None}) + "\n" + json.dumps({"id": "esc-2", "answered_at": "x"}) + "\n")
    d = TestClient(server.app).get("/api/live").json()
    assert d["escalations"] == 2 and d["unanswered"] == 1 and d["transcripts"] == 0
