import json
from northline.pm import propose as pr

CAND = {"persona": "patient", "proposed_tool": "request_refill", "count": 14, "share": 0.12, "quotes": ["Can someone call it in?"],
        "nearest_tools": ["escalate_to_nurse"], "description": "Refill needs a new script", "tier_mix": {"non_urgent_clinical": 14}}
OUT = {"tool_name": "request_refill", "description": "Request a prescription refill.", "input_schema": {"type": "object"},
       "backend_needed": "e-prescribing", "safety_notes": "Nurse approves.", "personas": ["patient"]}
QM = {"escalations_per_week": 2400, "nurse_response_median_h": 31.0, "nurse_response_p90_h": 70.0, "non_clinical_share_of_queue": 0.41,
      "unanswered_over_24h": 300, "patients_inactive_after_escalation": 280}


def test_proposal_schema_constrains_personas():
    assert pr.PROPOSAL_SCHEMA["properties"]["personas"]["items"]["enum"] == ["patient", "plan"]


def test_render_tool():
    t = pr.render_tool(CAND, OUT)
    assert "`request_refill`" in t and "12%" in t and "/expand tool-request_refill" in t and "{" not in t.split("```json")[0]


def test_render_deploy_has_four_decisions():
    t = pr.render_deploy(QM, {"agent_name": "triage", "placement": "between escalation and the nurse queue", "purpose": "p",
                              "tools_needed": ["pending_messages"], "decisions_for_humans": [], "acceptance_test": "Exhibit E",
                              "metrics_it_should_move": ["median response"], "risks": "downgrading"})
    assert t.count("\n1. ") == 1 and "4. " in t and "Urgent thresholds" in t and "/deploy triage" in t and "41%" in t


def test_main_clears_stale_tool_proposals(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "OUT", tmp_path)
    (tmp_path / "candidates.json").write_text(json.dumps([CAND]))
    (tmp_path / "queue_metrics.json").write_text(json.dumps(QM))
    (tmp_path / "proposals").mkdir()
    (tmp_path / "proposals" / "tool-old.md").write_text("stale")

    def fake(jobs, **kw):
        return [dict(OUT), {"agent_name": "triage", "placement": "p", "purpose": "p", "tools_needed": [],
                             "decisions_for_humans": [], "acceptance_test": "t", "metrics_it_should_move": [], "risks": "r"}]

    pr.main(top=1, ask=fake)
    proposals = tmp_path / "proposals"
    assert not (proposals / "tool-old.md").exists()
    assert (proposals / "tool-request_refill.md").exists()
    assert (proposals / "agent-triage.md").exists()
