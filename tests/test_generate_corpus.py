import json, statistics
from datetime import datetime
from northline.pm import generate_corpus as g


def test_plan_deterministic_and_has_refills():
    p = g.plan(60, seed=1)
    assert p == g.plan(60, seed=1) and sum("refill" in t for t, _ in p) >= 4 and sum("routine weekly check-in" in t for t, _ in p) >= 15


def test_queue_rows_shape():
    rows = g.queue_rows({"escalations_per_week": 2400, "nurse_response_median_h": 31.0}, n=2000, seed=2)
    assert len(rows) == 2000 and all(r["id"].startswith("corpus-esc-") for r in rows)
    answered = [(datetime.fromisoformat(r["answered_at"]) - datetime.fromisoformat(r["created_at"])).total_seconds() / 3600 for r in rows if r["answered_at"]]
    assert 0.98 <= len(answered) / 2000 <= 1.0 and 26 <= statistics.median(answered) <= 36
    after = sum(1 for r in rows if datetime.fromisoformat(r["created_at"]).weekday() >= 5 or not 8 <= datetime.fromisoformat(r["created_at"]).hour < 18)
    assert 0.42 <= after / 2000 <= 0.50


def test_exhibit_files():
    e = json.loads(open("northline/agents/triage/exhibit_e.json").read()); k = json.loads(open("northline/agents/triage/nurse_key.json").read())
    assert len(e) == 15 and e[11]["text"].startswith("BP was 184/112") and len(k["key"]) == 15 and k["key"][11]["tier"] == "urgent_clinical"


def test_valid_transcript():
    good = {"messages": [{"role": "assistant", "content": "Hi, time for your check-in. How's your BP?"},
                          {"role": "user", "content": "146/92, feeling fine."},
                          {"role": "assistant", "content": "Got it, logged."},
                          {"role": "user", "content": "Thanks."}],
            "tools_used": ["log_reading"], "escalated": False}
    assert g._valid_transcript(good)
    bad = {"messages": [{"role": "user", "content": "Write a realistic SMS conversation, 4 to 8 short texts, conversation number 3"}],
           "tools_used": [], "escalated": False}
    assert not g._valid_transcript(bad)


def test_valid_plan():
    good = {"calls": [{"tool": "member_engagement", "args": {"plan_id": "plan-prairie"}, "status": "ok"},
                       {"tool": "enrollment_status", "args": {"member_id": "555-1234"}, "status": "not_found"}]}
    assert g._valid_plan(good)
    bad = {"calls": [{"tool": "StructuredOutput", "args": {}, "status": "ok"}]}
    assert not g._valid_plan(bad)
