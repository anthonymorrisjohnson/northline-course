"""Append-only log of every tool call. This is the only product signal the MCP path gives you."""
import functools, json, os
from datetime import datetime, timezone
from pathlib import Path
_DEFAULT = Path(__file__).resolve().parents[1] / "logs"


def log_dir() -> Path:
    return Path(os.environ.get("NORTHLINE_LOG_DIR", _DEFAULT))


def log_call(tool: str, args: dict, result: dict, *, persona: str, session_id: str) -> None:
    d = log_dir(); d.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session_id": session_id, "persona": persona,
            "tool": tool, "args": args, "status": result.get("status", "unknown"),
            "error": result.get("message") if result.get("status") != "ok" else None}
    with (d / "tool_calls.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


def wrap(fn, *, persona: str, session_id: str):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        result = fn(*args, **kwargs)
        log_call(fn.__name__, kwargs, result, persona=persona, session_id=session_id)
        return result
    return inner
