"""Step 3 of the loop: arithmetic only. Unmet needs from the records, the bottleneck from the queue timestamps."""
import json, statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT = HERE / "out"
CASE = {"escalations_per_week": 2400, "nurse_response_median_h": 31, "after_hours_share": 0.46,
        "inbound_per_week": 3100, "overtime_hours_per_month": 1150, "inactive_after_escalation": 340}


def _dt(s):
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def load_queue(corpus_dir: Path, log_dir: Path) -> list[dict]:
    rows = []
    for p in (corpus_dir / "queue.jsonl", log_dir / "queue.jsonl"):
        if p.exists():
            rows += [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    return rows


def queue_metrics(rows: list[dict], weeks: float = 13.0) -> dict:
    if not rows:
        return {k: 0 for k in ("escalations_per_week", "answered_share", "nurse_response_median_h", "nurse_response_p90_h",
                               "after_hours_share", "non_clinical_share_of_queue", "unanswered_over_24h",
                               "patients_inactive_after_escalation", "urgent_median_h")}
    answered = [(_dt(r["answered_at"]) - _dt(r["created_at"])).total_seconds() / 3600 for r in rows if r.get("answered_at")]
    urgent = [(_dt(r["answered_at"]) - _dt(r["created_at"])).total_seconds() / 3600 for r in rows if r.get("answered_at") and r.get("urgency") == "urgent"]
    newest = max(_dt(r["created_at"]) for r in rows)
    unanswered = [r for r in rows if not r.get("answered_at") and (newest - _dt(r["created_at"])).total_seconds() > 86400]
    after = [r for r in rows if _dt(r["created_at"]).weekday() >= 5 or not 8 <= _dt(r["created_at"]).hour < 18]
    p90 = sorted(answered)[int(0.9 * (len(answered) - 1))] if answered else 0
    return {"escalations_per_week": round(len(rows) / weeks), "answered_share": round(len(answered) / len(rows), 2),
            "nurse_response_median_h": round(statistics.median(answered), 1) if answered else 0, "nurse_response_p90_h": round(p90, 1),
            "after_hours_share": round(len(after) / len(rows), 2),
            "non_clinical_share_of_queue": round(sum(1 for r in rows if r.get("tier") == "non_clinical") / len(rows), 2),
            "unanswered_over_24h": len(unanswered), "patients_inactive_after_escalation": len({r["patient_id"] for r in unanswered}),
            "urgent_median_h": round(statistics.median(urgent), 1) if urgent else 0}


def candidates(records: list[dict]) -> list[dict]:
    totals = Counter(r["persona"] for r in records)
    groups = defaultdict(list)
    for r in records:
        if r.get("unmet_need") and r.get("proposed_tool"):
            groups[(r["persona"], r["proposed_tool"])].append(r)
    out = []
    for (persona, tool), rs in groups.items():
        near = Counter(t for r in rs for t in r.get("tools_used", []))
        desc = Counter(r["unmet_need_description"] for r in rs if r.get("unmet_need_description"))
        out.append({"persona": persona, "proposed_tool": tool, "count": len(rs), "share": round(len(rs) / totals[persona], 2),
                    "quotes": [r["evidence_quote"] for r in rs if r.get("evidence_quote")][:3],
                    "nearest_tools": [t for t, _ in near.most_common(2)], "description": desc.most_common(1)[0][0] if desc else "",
                    "tier_mix": dict(Counter(r.get("tier", "none") for r in rs))})
    return sorted(out, key=lambda c: (-c["count"], c["proposed_tool"]))


def report(records, cands, qm, summary) -> str:
    board = {**CASE, **(summary or {}).get("last_quarter", {})} if summary else CASE
    L = ["# Northline PM loop report", "", f"{len(records)} conversations and sessions classified; {qm['escalations_per_week']} escalations a week in the queue log.", "",
         "## The board's numbers next to the logs", "", "| metric | Board deck | From logs |", "|---|---|---|",
         f"| Escalations per week | {board['escalations_per_week']} | {qm['escalations_per_week']} |",
         f"| Median nurse response (h) | {board['nurse_response_median_h']} | {qm['nurse_response_median_h']} (p90 {qm['nurse_response_p90_h']}) |",
         f"| Urgent escalations, median response (h) | not reported | {qm['urgent_median_h']} |",
         f"| After-hours share | {board['after_hours_share']} | {qm['after_hours_share']} |",
         f"| Non-clinical share of the nurse queue | not reported | {qm['non_clinical_share_of_queue']} |",
         f"| Patients inactive after an escalation | {board['inactive_after_escalation']} | {qm['patients_inactive_after_escalation']} |", ""]
    for persona in ("patient", "plan"):
        rs = [r for r in records if r["persona"] == persona]
        if rs:
            c = Counter(r["outcome"] for r in rs)
            L += [f"## Outcomes, {persona}", "", "| resolved | partial | failed | escalated |", "|---|---|---|---|",
                  f"| {c['resolved']} | {c['partial']} | {c['failed']} | {c['escalated']} |", ""]
    tiers = Counter(r["tier"] for r in records if r["persona"] == "patient")
    L += ["## What patients raise, by tier", "", "| urgent clinical | non-urgent clinical | non-clinical |", "|---|---|---|",
          f"| {tiers['urgent_clinical']} | {tiers['non_urgent_clinical']} | {tiers['non_clinical']} |", "",
          "## Candidate expansions", "", "| tool | persona | count | share | nearest existing | example |", "|---|---|---|---|---|---|"]
    for c in cands:
        L.append(f"| `{c['proposed_tool']}` | {c['persona']} | {c['count']} | {int(c['share'] * 100)}% | {', '.join(c['nearest_tools']) or '-'} | {(c['quotes'] or [c['description']])[0]} |")
    L += ["", f"Unanswered escalations: {qm['unanswered_over_24h']}, from {qm['patients_inactive_after_escalation']} patients.", ""]
    return "\n".join(L)


def main() -> None:
    records = [json.loads(l) for l in (OUT / "classified.jsonl").read_text().splitlines() if l.strip()]
    qm = queue_metrics(load_queue(REPO_ROOT / "corpus", REPO_ROOT / "northline" / "logs"))
    sp = REPO_ROOT / "northline" / "sim" / "out" / "summary.json"
    summary = json.loads(sp.read_text()) if sp.exists() else None
    cands = candidates(records)
    (OUT / "report.md").write_text(report(records, cands, qm, summary))
    (OUT / "candidates.json").write_text(json.dumps(cands, indent=2))
    (OUT / "queue_metrics.json").write_text(json.dumps(qm, indent=2))
    print(f"{len(cands)} candidates; median response {qm['nurse_response_median_h']}h -> {OUT / 'report.md'}")


if __name__ == "__main__":
    main()
