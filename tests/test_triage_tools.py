import json
from northline.tools import patient as p, triage as t


def _seed(data_dir, log_dir):
    p.escalate_to_nurse(patient_id="pt-1001", reason="BP 184/112 headache", urgency="urgent")
    p.escalate_to_nurse(patient_id="pt-1002", reason="insurance denied strips", urgency="routine")


def test_pending_lists_unrouted(data_dir, log_dir):
    _seed(data_dir, log_dir)
    r = t.pending_messages(limit=10)
    assert [m["id"] for m in r["messages"]] == ["esc-1", "esc-2"]


def test_tier_and_route(data_dir, log_dir):
    _seed(data_dir, log_dir)
    assert t.tier_message(message_id="esc-2", tier="non_clinical", rationale="benefits question")["status"] == "ok"
    assert t.tier_message(message_id="esc-2", tier="silly", rationale="")["status"] == "error"
    r = t.route_message(message_id="esc-2", to="admin", draft_reply="Our benefits team will call you tomorrow.")
    assert r["status"] == "ok"
    rows = [json.loads(l) for l in (log_dir / "queue.jsonl").read_text().splitlines()]
    assert rows[1]["route"] == "admin" and rows[1]["answered_at"] is not None and rows[0]["answered_at"] is None
    assert [m["id"] for m in t.pending_messages()["messages"]] == ["esc-1"]


def test_route_unknown(data_dir, log_dir):
    assert t.route_message(message_id="esc-9", to="admin")["status"] == "not_found"
