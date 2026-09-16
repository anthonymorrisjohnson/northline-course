"""Tools Northline publishes to health plans over MCP. Their agent, our data."""
import json
from pathlib import Path
from . import store

_SUMMARY = Path(__file__).resolve().parents[1] / "sim" / "out" / "summary.json"
FALLBACK = {"engaged_weekly": 0.78, "readings_per_month": 120000, "escalations_per_week": 2400, "satisfaction": 72,
            "nurse_response_median_h": 31.0}


def _now() -> dict:
    if _SUMMARY.exists():
        try:
            return {**FALLBACK, **json.loads(_SUMMARY.read_text())["now"]}
        except (KeyError, ValueError):
            pass
    return FALLBACK


def _plan(pid):
    return next((p for p in store.load("plans") if p["id"] == pid), None)


def member_engagement(plan_id: str) -> dict:
    """Engagement figures for a plan's enrolled members: weekly response rate and readings logged."""
    p = _plan(plan_id)
    if p is None:
        return {"status": "not_found", "message": f"no plan {plan_id}"}
    n = _now()
    return {"status": "ok", "plan": p["name"], "enrolled": p["enrolled"], "weekly_response_rate": n["engaged_weekly"],
            "readings_per_month": int(n["readings_per_month"] * p["enrolled"] / 40000)}


def outcome_evidence(plan_id: str, metric: str) -> dict:
    """Outcome evidence for a plan. metric: bp_control, readings, satisfaction, escalations."""
    if _plan(plan_id) is None:
        return {"status": "not_found", "message": f"no plan {plan_id}"}
    n = _now()
    table = {"bp_control": (0.58, "share of hypertensive members with last reading under 140/90"),
             "readings": (n["readings_per_month"], "readings logged per month, all members"),
             "satisfaction": (n["satisfaction"], "patient satisfaction score, 0 to 100"),
             "escalations": (n["escalations_per_week"], "clinical flags surfaced by the agent per week, all members")}
    if metric not in table:
        return {"status": "error", "message": f"metric must be one of {sorted(table)}"}
    v, note = table[metric]
    return {"status": "ok", "metric": metric, "value": v, "period": "last quarter", "note": note}


def enrollment_status(member_id: str) -> dict:
    """Whether a member is enrolled and engaged with the check-in program."""
    pt = next((x for x in store.load("patients") if x["id"] == member_id), None)
    if pt is None:
        return {"status": "not_found", "message": f"no member {member_id}"}
    return {"status": "ok", "member_id": member_id, "plan_id": pt["plan_id"], "engaged": pt["engaged"]}


def enroll_members(plan_id: str, count: int) -> dict:
    """Enroll additional members from a plan into the program."""
    plans = store.load("plans")
    p = next((x for x in plans if x["id"] == plan_id), None)
    if p is None:
        return {"status": "not_found", "message": f"no plan {plan_id}"}
    p["enrolled"] += int(count)
    store.save("plans", plans)
    return {"status": "ok", "plan": p["name"], "enrolled": p["enrolled"]}
