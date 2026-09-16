"""A weekly model of Northline Care. Small enough to read, calibrated to the case's two columns.

Deployments override parameters. That is the whole mechanism: deploy an agent, the company changes.
"""
import math
from dataclasses import dataclass, replace

MAX_RESPONSE_H = 336.0

BASE = {
    "nurse_capacity_items_per_week": 150, "hours_per_item": 0.27, "nurse_cost_month": 9000, "overtime_rate": 45, "fee": 25,
    "monthly_reach": 0.60, "readings_per_reach": 0.5,          # before: 40000 * 0.6 * 0.5 = 12,000 readings a month
    "engaged_weekly": 0.0, "readings_per_response": 0.89,      # agent: 40000 * 0.78 * 4.33 * 0.89 = 120,000
    "escalation_rate": 0.0075, "inbound_rate": 0.0, "after_hours_share": 0.46,
    "urgent_share_of_escalations": 0.15, "inbound_to_nurse_share": 0.60, "routine_time_factor": 1.0,
    "urgent_recall": 1.0, "response_curve": 4.5, "resignation_rate": 0.02, "disengage_rate": 0.021,
    "baseline_overtime_month": 180,  # overtime that exists regardless of load; the case's before column
}


@dataclass(frozen=True)
class State:
    week: int
    patients: int
    nurses: int
    resign_accum: float
    inactive_total: int


def params_for(week: int, deployments: list[dict]) -> dict:
    p = dict(BASE)
    for d in deployments:
        if d.get("live_from_week", 1) <= week:
            p.update(d.get("effects", {}))
    return p


def step(s: State, p: dict) -> tuple[State, dict]:
    P, N = s.patients, s.nurses
    if p["engaged_weekly"] > 0:
        readings = P * p["engaged_weekly"] * 4.33 * p["readings_per_response"]
    else:
        readings = P * p["monthly_reach"] * p["readings_per_reach"]
    esc = P * p["escalation_rate"]
    inbound = P * p["inbound_rate"]
    urgent = esc * p["urgent_share_of_escalations"]
    items = urgent + (esc - urgent) * p["routine_time_factor"] + inbound * p["inbound_to_nurse_share"]
    capacity = N * p["nurse_capacity_items_per_week"]
    load = items / capacity if capacity else 99.0
    median_h = round(min(MAX_RESPONSE_H, 4.0 * math.exp(p["response_curve"] * max(0.0, load - 0.8))), 1)  # capped at two weeks; beyond that the number stops meaning anything
    urgent_h = 4.0 if p["routine_time_factor"] < 1.0 else median_h   # a triage layer sees urgent items first
    overtime = p["baseline_overtime_month"] + max(0.0, items - capacity) * p["hours_per_item"] * 4.33
    accum = s.resign_accum + N * p["resignation_rate"] * max(0.0, load - 1.0)
    resigned = int(accum); accum -= resigned
    unanswered_share = min(0.9, max(0.0, (median_h - 4.0) / (median_h + 20.0)))
    inactive_new = int(round(esc * unanswered_share * p["disengage_rate"]))
    missed_urgent = urgent * (1.0 - p["urgent_recall"])
    satisfaction = round(41 + 36 * (1 if p["engaged_weekly"] > 0 else 0) - 9 * min(1.0, (median_h - 4.0) / 48.0), 1)
    row = {"week": s.week, "patients": P, "nurses": N, "readings_per_month": round(readings), "escalations_per_week": round(esc),
           "inbound_per_week": round(inbound), "after_hours_share": p["after_hours_share"] if inbound else 0.0,
           "nurse_items_per_week": round(items), "load": round(load, 3), "nurse_response_median_h": median_h,
           "urgent_response_h": urgent_h, "overtime_hours_per_month": round(overtime), "resignations": resigned,
           "inactive_after_escalation": inactive_new, "missed_urgent_per_week": round(missed_urgent, 1),
           "satisfaction": satisfaction, "revenue_month": P * p["fee"],
           "nurse_cost_month": round(N * p["nurse_cost_month"] + overtime * p["overtime_rate"])}
    return State(s.week + 1, P, N - resigned, accum, s.inactive_total + inactive_new), row


def run(weeks: range, deployments: list[dict], start: State | None = None, patients: int | None = None) -> list[dict]:
    s = start or State(weeks.start, 40000, 25, 0.0, 0)
    s = replace(s, week=weeks.start, patients=patients or s.patients)
    rows = []
    for w in weeks:
        s, row = step(s, params_for(w, deployments)); rows.append(row)
    return rows


SUMMED = {"resignations", "inactive_after_escalation"}


def average(rows: list[dict]) -> dict:
    out = {}
    for k in rows[0]:
        vals = [r[k] for r in rows]
        out[k] = sum(vals) if k in SUMMED else round(sum(vals) / len(vals), 2)
    out["week"] = rows[-1]["week"]
    return out
