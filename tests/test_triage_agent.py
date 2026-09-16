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
