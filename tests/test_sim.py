import json
from pathlib import Path

from northline.sim import model as m

SUMMARY_PATH = Path(__file__).resolve().parents[1] / "northline" / "sim" / "out" / "summary.json"

CHECKIN = [{"name": "checkin_agent", "live_from_week": 1,
            "effects": {"engaged_weekly": 0.78, "escalation_rate": 0.06, "inbound_rate": 0.0775, "readings_per_response": 0.89}}]


def close(a, b, tol=0.10):
    return abs(a - b) <= tol * b


def test_before_column():
    _, r = m.step(m.State(0, 40000, 25, 0.0, 0), m.params_for(0, []))
    assert close(r["readings_per_month"], 12000) and close(r["escalations_per_week"], 300)
    assert r["nurse_response_median_h"] == 4.0 and close(r["overtime_hours_per_month"], 180, 0.2) and close(r["satisfaction"], 41, 0.05)


def test_last_quarter_column():
    rows = m.run(range(1, 40), CHECKIN)
    lq = m.average(rows[26:])
    assert close(lq["readings_per_month"], 120000) and close(lq["escalations_per_week"], 2400)
    assert close(lq["inbound_per_week"], 3100) and lq["after_hours_share"] == 0.46
    assert close(lq["nurse_response_median_h"], 31) and close(lq["overtime_hours_per_month"], 1150)
    assert 21 <= rows[-1]["nurses"] <= 23 and 2 <= lq["resignations"] <= 4
    assert close(lq["inactive_after_escalation"], 340, 0.15) and close(lq["satisfaction"], 72, 0.05)


def test_triage_effects_lower_response_time():
    hist = m.run(range(1, 40), CHECKIN)
    start = m.State(39, 40000, hist[-1]["nurses"], 0.0, 0)
    triage = CHECKIN + [{"name": "triage", "live_from_week": 40,
                         "effects": {"inbound_to_nurse_share": 0.25, "routine_time_factor": 0.6, "urgent_recall": 0.8}}]
    with_t = m.average(m.run(range(40, 53), triage, start=start))
    without = m.average(m.run(range(40, 53), CHECKIN, start=start))
    assert with_t["nurse_response_median_h"] < without["nurse_response_median_h"] / 2
    assert with_t["missed_urgent_per_week"] > 0 and without["missed_urgent_per_week"] == 0


def test_prairie_projection_without_triage_is_worse():
    hist = m.run(range(1, 40), CHECKIN)
    start = m.State(39, 40000, hist[-1]["nurses"], 0.0, 0)
    p = m.average(m.run(range(40, 53), CHECKIN, start=start, patients=100000))
    assert p["nurse_response_median_h"] > 60


def test_response_is_capped():
    rows = m.run(range(40, 53), CHECKIN, start=m.State(39, 40000, 16, 0.0, 0), patients=100000)
    assert all(r["nurse_response_median_h"] <= 336.0 for r in rows)
    assert m.average(rows)["nurse_response_median_h"] > 60


def test_summary_feeds_plan_tools():
    summary = json.loads(SUMMARY_PATH.read_text())
    assert close(summary["now"]["satisfaction"], 72)
    assert close(summary["now"]["escalations_per_week"], 2400)
