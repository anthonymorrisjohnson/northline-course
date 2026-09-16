"""One JSON file per check-in conversation. This is the product signal the controlled agent gives you."""
import json
from datetime import datetime, timezone
from pathlib import Path
from northline.tools.calllog import log_dir
from .claude_runner import TurnResult


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_turn(session_id: str, user: str, result: TurnResult) -> Path:
    d = log_dir() / "transcripts"; d.mkdir(parents=True, exist_ok=True)
    path = d / f"{session_id}.json"
    doc = json.loads(path.read_text()) if path.exists() else {
        "session_id": session_id, "persona": "patient", "started": _now(), "messages": [], "tool_uses": [],
        "escalated": False, "cost_usd": 0.0}
    doc["messages"] += [{"role": "user", "content": user, "ts": _now()}, {"role": "assistant", "content": result.reply, "ts": _now()}]
    doc["tool_uses"] += result.tool_uses
    doc["escalated"] = doc["escalated"] or any(t["name"] == "escalate_to_nurse" for t in result.tool_uses)
    doc["cost_usd"] = round(doc["cost_usd"] + result.cost_usd, 6)
    path.write_text(json.dumps(doc, indent=2))
    return path


def load_all(directory: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(directory).glob("*.json"))]
