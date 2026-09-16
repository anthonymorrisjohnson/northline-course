import json
from pathlib import Path
from northline.pm import aggregate as ag
FX = Path(__file__).parent / "fixtures"
RECS = [json.loads(l) for l in (FX / "classified.jsonl").read_text().splitlines()]
Q = [json.loads(l) for l in (FX / "queue.jsonl").read_text().splitlines()]


def test_queue_metrics():
    m = ag.queue_metrics(Q, weeks=1.0)
    assert m["escalations_per_week"] == 8 and m["nurse_response_median_h"] == 30.0
    assert m["after_hours_share"] == 0.38 and m["non_clinical_share_of_queue"] == 0.38
    assert m["unanswered_over_24h"] == 2 and m["patients_inactive_after_escalation"] == 2 and m["urgent_median_h"] == 40.0


def test_candidates():
    c = ag.candidates(RECS)
    assert c[0]["proposed_tool"] == "request_refill" and c[0]["count"] == 2 and c[0]["share"] == 0.4
    assert c[0]["quotes"] == ["Can someone call it in?", "I run out Thursday"]


def test_report_mentions_both_columns():
    r = ag.report(RECS, ag.candidates(RECS), ag.queue_metrics(Q, weeks=1.0), None)
    assert "Board deck" in r and "From logs" in r and "request_refill" in r and "Unanswered escalations: 2, from 2 patients." in r


def test_queue_metrics_mixes_naive_and_aware():
    rows = [
        {"created_at": "2026-09-07T09:00:00", "answered_at": "2026-09-07T13:00:00"},
        {"created_at": "2026-09-07T10:00:00+00:00", "answered_at": "2026-09-08T10:00:00+00:00"},
    ]
    m = ag.queue_metrics(rows, weeks=1.0)
    assert m["nurse_response_median_h"] == 14.0
