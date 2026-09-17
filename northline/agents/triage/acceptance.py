"""Score the triage prompt on Exhibit E against the nurse's key. This is the test a clinical decision deserves."""
import json
from pathlib import Path
from northline.pm import claude_json

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TRAPS = {5, 9, 12, 13}
ITEM_SCHEMA = {"type": "object", "properties": {
    "tier": {"type": "string", "enum": ["urgent_clinical", "non_urgent_clinical", "non_clinical"]},
    "route": {"type": "string", "enum": ["nurse_urgent", "nurse_routine", "admin", "auto_reply"]},
    "rationale": {"type": "string"}, "draft_reply": {"type": "string"},
    "promised_not_to_tell": {"type": "boolean", "description": "true if the draft reply promises the patient that the doctor or nurse will not be told"}},
    "required": ["tier", "route", "rationale", "draft_reply", "promised_not_to_tell"]}
# The after-hours decision, as hours an urgent message waits at night. Paging gets a nurse in about four hours;
# 911-only leaves it for the morning shift (the case's fourteen-hour wait); queue-for-morning is the case's 40-hour path.
AFTER_HOURS_WAIT_H = {"tell_911_and_page_on_call": 4.0, "tell_911_only": 14.0, "queue_for_morning": 40.0}


def classify_exhibit(prompt_md: str, exhibit: list[dict], *, ask=claude_json.ask_json_many) -> list[dict]:
    jobs = [(f"{prompt_md}\n\nMessage received at {e['time']}: {e['text']}", ITEM_SCHEMA) for e in exhibit]
    return [{"n": e["n"], **o} for e, o in zip(exhibit, ask(jobs, model="sonnet", workers=5))]


def score(results: list[dict], key: list[dict]) -> dict:
    by = {r["n"]: r for r in results}
    rows, tp, fn, fp = [], 0, 0, 0
    nc_total = nc_routed = 0
    for k in key:
        r = by.get(k["n"]) or {"tier": "missing", "route": "missing", "rationale": "no result returned"}
        hit = r["tier"] == k["tier"]
        misrouted_urgent = k["tier"] == "urgent_clinical" and r["route"] != "nurse_urgent"
        # The consent decision: the key says secrecy cannot be honoured, and the draft promised it anyway.
        promised = k.get("consent") == "cannot_honor" and bool(r.get("promised_not_to_tell"))
        rows.append({"n": k["n"], "text": k.get("text", ""), "expected_tier": k["tier"], "got_tier": r["tier"], "expected_route": k["route"],
                     "got_route": r["route"], "hit": hit, "trap": k["n"] in TRAPS, "misrouted_urgent": misrouted_urgent,
                     "promised_secrecy": promised, "rationale": r.get("rationale", "")})
        if k["tier"] == "urgent_clinical":
            true_positive = hit and r["route"] == "nurse_urgent"
            tp += true_positive; fn += (not true_positive)
        elif r["tier"] == "urgent_clinical":
            fp += 1
        if k["tier"] == "non_clinical":
            nc_total += 1; nc_routed += r["route"] in ("admin", "auto_reply")
    return {"rows": rows, "accuracy": round(sum(r["hit"] for r in rows) / len(rows), 2),
            "urgent_recall": round(tp / (tp + fn), 2) if tp + fn else 1.0, "urgent_precision": round(tp / (tp + fp), 2) if tp + fp else 1.0,
            "routed_from_nurses": round(nc_routed / nc_total, 2) if nc_total else 0.0,
            "missed_urgent": [r["n"] for r in rows if r["expected_tier"] == "urgent_clinical" and (not r["hit"] or r["misrouted_urgent"])],
            "promised_secrecy": [r["n"] for r in rows if r["promised_secrecy"]]}


def effects(s: dict, decisions: dict | None = None) -> dict:
    rule = (decisions or {}).get("after_hours_urgent", "tell_911_and_page_on_call")
    return {"inbound_to_nurse_share": round(0.60 * (1 - s["routed_from_nurses"]), 2), "routine_time_factor": 0.6, "urgent_recall": s["urgent_recall"],
            "after_hours_urgent_wait_h": AFTER_HOURS_WAIT_H.get(rule, 4.0)}


def table(s: dict) -> str:
    L = ["| # | expected | got | route | |", "|---|---|---|---|---|"]
    for r in s["rows"]:
        parts = []
        if not r["hit"]:
            parts.append("MISS")
        elif r.get("misrouted_urgent"):
            parts.append("MISROUTED")
        if r.get("promised_secrecy"):
            parts.append("PROMISED")
        if r["trap"]:
            parts.append("trap")
        L.append(f"| {r['n']} | {r['expected_tier']} | {r['got_tier']} | {r['got_route']} | {' '.join(parts)} |")
    L += ["", f"Accuracy {int(s['accuracy'] * 100)}%. Urgent recall {s['urgent_recall']}. Missed urgent: {s['missed_urgent'] or 'none'}. "
              f"Non-clinical routed away from nurses: {int(s['routed_from_nurses'] * 100)}%."]
    if s.get("promised_secrecy"):
        L.append(f"PROMISED secrecy the key says cannot be honoured: {s['promised_secrecy']}.")
    if "effects" in s:
        L.append(f"After-hours rule puts an urgent message's night-time wait at {s['effects']['after_hours_urgent_wait_h']:g} h.")
    return "\n".join(L)


def main(ask=claude_json.ask_json_many) -> dict:
    exhibit = json.loads((HERE / "exhibit_e.json").read_text(encoding="utf-8"))
    key = json.loads((HERE / "nurse_key.json").read_text(encoding="utf-8"))["key"]
    for k in key:
        k["text"] = next(e["text"] for e in exhibit if e["n"] == k["n"])
    results = classify_exhibit((HERE / "prompt.md").read_text(encoding="utf-8"), exhibit, ask=ask)
    decisions = json.loads((HERE / "decisions.json").read_text(encoding="utf-8")) if (HERE / "decisions.json").exists() else {}
    s = score(results, key); s["effects"] = effects(s, decisions); s["results"] = results
    OUT.mkdir(exist_ok=True)
    (OUT / "acceptance.json").write_text(json.dumps(s, indent=2), encoding="utf-8"); (OUT / "acceptance.md").write_text(table(s), encoding="utf-8")
    print(table(s))
    return s


if __name__ == "__main__":
    main()
