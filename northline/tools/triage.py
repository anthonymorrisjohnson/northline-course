"""Tools the triage agent uses on the nurse queue. Exposed only once triage is deployed."""
import json
from datetime import datetime, timezone
from typing import Any
from .patient import _log_dir

TIERS = {"urgent_clinical", "non_urgent_clinical", "non_clinical"}
ROUTES = {"nurse_urgent", "nurse_routine", "admin", "auto_reply"}


def _rows() -> list[dict]:
    q = _log_dir() / "queue.jsonl"
    return [json.loads(l) for l in q.read_text(encoding="utf-8").splitlines() if l.strip()] if q.exists() else []


def _write(rows: list[dict]) -> None:
    (_log_dir() / "queue.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _update(message_id: str, **fields) -> dict:
    rows = _rows()
    row = next((r for r in rows if r["id"] == message_id), None)
    if row is None:
        return {"status": "not_found", "message": f"no message {message_id}"}
    row.update(fields); _write(rows)
    return {"status": "ok", "message_id": message_id}


def pending_messages(limit: int = 20) -> dict[str, Any]:
    """Oldest unrouted messages in the nurse queue: id, patient_id, reason, urgency, created_at."""
    rows = [r for r in _rows() if r["answered_at"] is None and r.get("route") is None]
    return {"status": "ok" if rows else "not_found", "messages": rows[:limit]}


def tier_message(message_id: str, tier: str, rationale: str) -> dict[str, Any]:
    """Assign a tier: urgent_clinical, non_urgent_clinical, or non_clinical, with a one-line rationale."""
    if tier not in TIERS:
        return {"status": "error", "message": f"tier must be one of {sorted(TIERS)}"}
    return _update(message_id, tier=tier, rationale=rationale)


def route_message(message_id: str, to: str, draft_reply: str = "") -> dict[str, Any]:
    """Route a message: nurse_urgent, nurse_routine, admin, or auto_reply. Include a draft reply for a nurse to review."""
    if to not in ROUTES:
        return {"status": "error", "message": f"to must be one of {sorted(ROUTES)}"}
    fields = {"route": to, "draft_reply": draft_reply}
    if to in ("admin", "auto_reply"):
        fields["answered_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return _update(message_id, **fields)
