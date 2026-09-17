import json
from pathlib import Path
from northline.agents.triage import render, acceptance as ac

KEY = json.loads(Path("northline/agents/triage/nurse_key.json").read_text())["key"]


def test_render_fills_all_placeholders():
    p = render.render(render.DEFAULTS)
    assert "{" not in p and "180/110" in p and "northline_default" in p and "Apply the thresholds literally" in p


def test_render_strict_threshold_changes_prompt():
    d = json.loads(json.dumps(render.DEFAULTS)); d["urgent"]["systolic"] = 190; d["chosen_by"] = "attendee"
    assert "190/110" in render.render(d)


def _results(overrides: dict) -> list[dict]:
    out = []
    for k in KEY:
        r = {"n": k["n"], "tier": k["tier"], "route": k["route"], "rationale": "", "draft_reply": ""}
        r.update(overrides.get(k["n"], {})); out.append(r)
    return out


def test_score_perfect():
    s = ac.score(_results({}), KEY)
    assert s["accuracy"] == 1.0 and s["urgent_recall"] == 1.0 and s["missed_urgent"] == [] and s["routed_from_nurses"] == 1.0


def test_score_downgrades_message_12():
    s = ac.score(_results({12: {"tier": "non_urgent_clinical", "route": "nurse_routine"}}), KEY)
    assert s["missed_urgent"] == [12] and s["urgent_recall"] == 0.75
    row = next(r for r in s["rows"] if r["n"] == 12)
    assert row["hit"] is False and row["trap"] is True and "MISS" in ac.table(s)


def test_effects_from_score():
    s = ac.score(_results({2: {"route": "nurse_routine"}}), KEY)
    e = ac.effects(s)
    assert e["urgent_recall"] == 1.0 and e["routine_time_factor"] == 0.6 and 0.6 * (1 - s["routed_from_nurses"]) - 0.01 < e["inbound_to_nurse_share"] < 0.6


def test_score_missing_result_is_a_miss():
    results = [r for r in _results({}) if r["n"] != 7]
    s = ac.score(results, KEY)
    row = next(r for r in s["rows"] if r["n"] == 7)
    assert row["hit"] is False and row["got_tier"] == "missing"
    assert s["accuracy"] == round(14 / 15, 2)


def test_score_misrouted_urgent_counts_as_missed():
    s = ac.score(_results({4: {"route": "nurse_routine"}}), KEY)
    assert s["missed_urgent"] == [4] and s["urgent_recall"] == 0.75
    assert "MISROUTED" in ac.table(s)


def test_consent_promise_is_marked_and_after_hours_rule_sets_wait():
    from northline.agents.triage import acceptance as a
    key = [{"n": 13, "tier": "non_urgent_clinical", "route": "nurse_routine", "consent": "cannot_honor", "note": ""}]
    s = a.score([{"n": 13, "tier": "non_urgent_clinical", "route": "nurse_routine", "rationale": "", "promised_not_to_tell": True}], key)
    assert s["promised_secrecy"] == [13] and s["accuracy"] == 1.0
    assert "PROMISED" in a.table(s)
    assert a.effects(s, {"after_hours_urgent": "queue_for_morning"})["after_hours_urgent_wait_h"] == 40.0
    assert a.effects(s, {"after_hours_urgent": "tell_911_and_page_on_call"})["after_hours_urgent_wait_h"] == 4.0
    assert a.effects(s)["after_hours_urgent_wait_h"] == 4.0


def test_after_hours_wait_reaches_urgent_response_in_the_model():
    from northline.sim import model as m
    base = {"engaged_weekly": 0.78, "escalation_rate": 0.06, "inbound_rate": 0.0775, "readings_per_response": 0.89,
            "inbound_to_nurse_share": 0.0, "routine_time_factor": 0.6, "urgent_recall": 1.0}
    paged = m.step(m.State(40, 40000, 22, 0.0, 0), {**m.BASE, **base, "after_hours_urgent_wait_h": 4.0})[1]
    morning = m.step(m.State(40, 40000, 22, 0.0, 0), {**m.BASE, **base, "after_hours_urgent_wait_h": 40.0})[1]
    assert paged["urgent_response_h"] == 4.0 and 20 <= morning["urgent_response_h"] <= 21
    assert paged["nurse_response_median_h"] == morning["nurse_response_median_h"]
