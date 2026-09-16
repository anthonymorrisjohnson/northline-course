import json
from northline.tools import patient as p, store


def test_log_reading_flags_high_bp(data_dir, log_dir):
    r = p.log_reading(patient_id="pt-1001", kind="bp", value="184/112")
    assert r["status"] == "ok" and r["flag"] == "high"
    assert store.load("readings")[-1]["value"] == "184/112"


def test_log_reading_low_glucose(data_dir, log_dir):
    assert p.log_reading(patient_id="pt-1001", kind="glucose", value="62")["flag"] == "low"


def test_log_reading_unknown_patient(data_dir, log_dir):
    assert p.log_reading(patient_id="zz", kind="bp", value="120/80")["status"] == "not_found"


def test_log_medication(data_dir, log_dir):
    assert p.log_medication(patient_id="pt-1002", taken=False, note="upsets stomach")["status"] == "ok"


def test_escalate_writes_queue(data_dir, log_dir):
    r = p.escalate_to_nurse(patient_id="pt-1001", reason="BP 184/112 with headache", urgency="urgent")
    assert r["status"] == "ok" and r["escalation_id"] == "esc-1"
    row = json.loads((log_dir / "queue.jsonl").read_text().strip())
    assert row["answered_at"] is None and row["urgency"] == "urgent"
    assert "hours" in r["message"]


def test_next_checkin(data_dir, log_dir):
    assert p.next_checkin(patient_id="pt-1001")["next"].endswith("T09:00")
