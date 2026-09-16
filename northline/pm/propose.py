"""Step 5 of the loop: draft specs. Tools for unmet needs; an agent deployment for the queue. Humans approve."""
import json
from pathlib import Path
from . import claude_json

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT = HERE / "out"
T = REPO_ROOT / "templates"
PROPOSAL_SCHEMA = {"type": "object", "properties": {"tool_name": {"type": "string"}, "description": {"type": "string"},
                   "input_schema": {"type": "object"}, "backend_needed": {"type": "string"}, "safety_notes": {"type": "string"},
                   "personas": {"type": "array", "items": {"type": "string"}}},
                   "required": ["tool_name", "description", "input_schema", "backend_needed", "safety_notes", "personas"]}
DEPLOY_SCHEMA = {"type": "object", "properties": {"agent_name": {"type": "string"}, "placement": {"type": "string"}, "purpose": {"type": "string"},
                 "tools_needed": {"type": "array", "items": {"type": "string"}}, "decisions_for_humans": {"type": "array", "items": {"type": "string"}},
                 "acceptance_test": {"type": "string"}, "metrics_it_should_move": {"type": "array", "items": {"type": "string"}}, "risks": {"type": "string"}},
                 "required": ["agent_name", "placement", "purpose", "tools_needed", "decisions_for_humans", "acceptance_test", "metrics_it_should_move", "risks"]}
TRIAGE_DECISIONS = [
    "Urgent thresholds: the systolic and diastolic blood pressure, the low and high glucose, and the symptom words that are always urgent.",
    "Non-clinical handling: route to admin staff, auto-reply from approved content, or hold for the morning.",
    "After-hours rule: what happens to an urgent message at 1:48am when no nurse is on shift.",
    "Consent: whether 'don't tell the doctor' is honoured, and what the patient is told either way.",
]


def _fill(template: str, fill: dict) -> str:
    for k, v in fill.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def render_tool(c: dict, o: dict) -> str:
    stem = f"tool-{c['proposed_tool']}"
    return _fill((T / "expansion-proposal.md").read_text(), {
        "tool_name": o["tool_name"], "personas": ", ".join(o["personas"]), "count": c["count"], "share": int(c["share"] * 100),
        "persona": c["persona"], "description": c["description"], "quotes": "\n".join(f'- "{q}"' for q in c["quotes"]) or "- (none)",
        "tool_description": o["description"], "input_schema": json.dumps(o["input_schema"], indent=2),
        "nearest_tools": ", ".join(c["nearest_tools"]) or "-", "backend_needed": o["backend_needed"], "safety_notes": o["safety_notes"], "file_stem": stem})


def render_deploy(qm: dict, o: dict) -> str:
    decisions = TRIAGE_DECISIONS if o["agent_name"] == "triage" else o["decisions_for_humans"]
    return _fill((T / "deployment-proposal.md").read_text(), {
        "agent_name": o["agent_name"], "placement": o["placement"], "purpose": o["purpose"],
        "escalations_per_week": qm["escalations_per_week"], "median_h": qm["nurse_response_median_h"], "p90_h": qm["nurse_response_p90_h"],
        "non_clinical_pct": int(qm["non_clinical_share_of_queue"] * 100), "unanswered": qm["unanswered_over_24h"], "inactive": qm["patients_inactive_after_escalation"],
        "tools_needed": "\n".join(f"- `{t}`" for t in o["tools_needed"]), "decisions": "\n".join(f"{i + 1}. {d}" for i, d in enumerate(decisions)),
        "acceptance_test": o["acceptance_test"], "metrics": "\n".join(f"- {m}" for m in o["metrics_it_should_move"]), "risks": o["risks"]})


def _tool_prompt(c):
    return (f"You are the product manager at Northline Care, a rural chronic-care company with an SMS check-in agent. Patients asked {c['count']} times "
            f"for something no tool can do: {c['description']}. Quotes: {c['quotes']}. Nearest tools: {c['nearest_tools']}. Draft a tool named "
            f"{c['proposed_tool']}: a one-sentence docstring, a JSON input schema with snake_case fields including patient_id, the backend it needs, "
            f"and safety notes. Patients never receive clinical advice through a tool; if this request is clinical, design the tool to route to a nurse with the right context.")


def _deploy_prompt(qm):
    return (f"You are the product manager at Northline Care. The nurse queue shows {qm['escalations_per_week']} escalations a week, median response "
            f"{qm['nurse_response_median_h']}h, {int(qm['non_clinical_share_of_queue'] * 100)}% non-clinical items, {qm['unanswered_over_24h']} unanswered over 24h. "
            f"Draft a deployment proposal for an agent named triage that sits between the check-in agent's escalations and the nurse queue. It has tools "
            f"pending_messages, tier_message, route_message. Describe placement, purpose, the acceptance test (the fifteen night texts in Exhibit E scored against "
            f"a nurse's key), the metrics it should move, and the risks, especially downgrading an urgent case. Leave decisions_for_humans empty; they are fixed.")


def main(top: int = 4, ask=claude_json.ask_json_many) -> None:
    cands = json.loads((OUT / "candidates.json").read_text())[:top]
    qm = json.loads((OUT / "queue_metrics.json").read_text())
    outs = ask([(_tool_prompt(c), PROPOSAL_SCHEMA) for c in cands] + [(_deploy_prompt(qm), DEPLOY_SCHEMA)], model="sonnet")
    (OUT / "proposals").mkdir(exist_ok=True)
    for p in (OUT / "proposals").glob("tool-*.md"):
        p.unlink()
    for c, o in zip(cands, outs[:-1]):
        (OUT / "proposals" / f"tool-{c['proposed_tool']}.md").write_text(render_tool(c, o))
    d = outs[-1]; d["agent_name"] = "triage"
    (OUT / "proposals" / "agent-triage.md").write_text(render_deploy(qm, d))
    print(f"wrote {len(cands)} tool proposals and agent-triage.md")


if __name__ == "__main__":
    main()
