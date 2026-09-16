"""Patient-facing tools for the weekly check-in agent. Administrative only."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from . import store
from .calllog import log_dir as _log_dir

_ROOT = Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _patient(pid):
    return next((x for x in store.load("patients") if x["id"] == pid), None)


def _flag(kind: str, value: str) -> str:
    try:
        value = str(value)
        if kind == "bp":
            s, d = (int(x) for x in value.split("/"))
            return "high" if s >= 160 or d >= 100 else "normal"
        g = float(value)
        return "low" if g < 70 else "high" if g > 250 else "normal"
    except (ValueError, AttributeError, TypeError):
        return "normal"


def log_reading(patient_id: str, kind: str, value: str) -> dict[str, Any]:
    """Log a blood pressure (kind 'bp', value like '146/92') or glucose (kind 'glucose', value like '62') reading."""
    pts = store.load("patients")
    pt = next((x for x in pts if x["id"] == patient_id), None)
    if pt is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    if kind not in ("bp", "glucose"):
        return {"status": "error", "message": "kind must be bp or glucose"}
    row = store.append("readings", {"id": f"rd-{len(store.load('readings')) + 1}", "patient_id": patient_id,
                                    "kind": kind, "value": value, "at": _now(), "flag": _flag(kind, value)})
    pt.setdefault("last_readings", []).append({"kind": kind, "value": value, "at": row["at"]})
    store.save("patients", pts)
    return {"status": "ok", "reading_id": row["id"], "flag": row["flag"]}


def log_medication(patient_id: str, taken: bool, note: str = "") -> dict[str, Any]:
    """Record whether the patient took their medication this week, with an optional note."""
    if _patient(patient_id) is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    store.append("medication_log", {"patient_id": patient_id, "taken": taken, "note": note, "at": _now()})
    return {"status": "ok"}


def _median_hours() -> float:
    p = _ROOT / "sim" / "out" / "summary.json"
    if p.exists():
        try:
            return round(json.loads(p.read_text(encoding="utf-8"))["now"]["nurse_response_median_h"], 1)
        except (KeyError, ValueError):
            pass
    return 31.0


def escalate_to_nurse(patient_id: str, reason: str, urgency: str = "routine") -> dict[str, Any]:
    """Hand a concerning reading or symptom to a nurse. urgency is 'routine' or 'urgent'. Use for any clinical question."""
    if _patient(patient_id) is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    d = _log_dir(); d.mkdir(parents=True, exist_ok=True)
    q = d / "queue.jsonl"
    n = sum(1 for _ in q.open(encoding="utf-8")) + 1 if q.exists() else 1
    row = {"id": f"esc-{n}", "patient_id": patient_id, "reason": reason, "urgency": urgency,
           "created_at": _now(), "answered_at": None, "tier": None, "route": None}
    with q.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return {"status": "ok", "escalation_id": row["id"],
            "message": f"A nurse will review this. Median response time is currently {_median_hours()} hours."}


def next_checkin(patient_id: str) -> dict[str, Any]:
    """When the patient's next weekly check-in is due."""
    if _patient(patient_id) is None:
        return {"status": "not_found", "message": f"no patient {patient_id}"}
    today = datetime.now().date()
    nxt = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
    return {"status": "ok", "next": f"{nxt.isoformat()}T09:00"}
