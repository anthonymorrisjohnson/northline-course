from northline.tools import plan as pl, store


def test_engagement_fallback(data_dir, log_dir, monkeypatch, tmp_path):
    monkeypatch.setattr(pl, "_SUMMARY", tmp_path / "missing.json")
    r = pl.member_engagement(plan_id="plan-prairie")
    assert r["status"] == "ok" and r["weekly_response_rate"] == 0.78 and r["enrolled"] == 2000


def test_outcome_metrics(data_dir, log_dir, monkeypatch, tmp_path):
    monkeypatch.setattr(pl, "_SUMMARY", tmp_path / "missing.json")
    assert pl.outcome_evidence(plan_id="plan-prairie", metric="satisfaction")["value"] == 72
    assert pl.outcome_evidence(plan_id="plan-prairie", metric="escalations")["value"] == 2400
    assert pl.outcome_evidence(plan_id="plan-prairie", metric="nope")["status"] == "error"


def test_enrollment(data_dir, log_dir, monkeypatch, tmp_path):
    monkeypatch.setattr(pl, "_SUMMARY", tmp_path / "missing.json")
    assert pl.enrollment_status(member_id="pt-1001")["status"] == "ok"
    assert pl.enroll_members(plan_id="plan-prairie", count=100)["enrolled"] == 2100
    assert next(p for p in store.load("plans") if p["id"] == "plan-prairie")["enrolled"] == 2100
