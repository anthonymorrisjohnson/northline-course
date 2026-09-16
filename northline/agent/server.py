"""Front door 2: the check-in agent as an SMS-style page. The dashboard is served here too."""
import json, os, re, uuid
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from . import claude_runner, prompt, transcripts
from northline.tools.calllog import log_dir
from northline.sim import run as sim_run

app = FastAPI(title="Northline check-in agent")
STATIC = Path(__file__).resolve().parent / "static"
SIM_OUT = sim_run.OUT
run_turn_fn = claude_runner.run_turn
_claude_sessions: dict[str, str] = {}
SESSION_RE = re.compile(r"^[0-9a-f]{12}$")


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/dashboard")
def dashboard():
    return FileResponse(STATIC / "dashboard.html")


@app.get("/api/sim")
def api_sim():
    if not (SIM_OUT / "summary.json").exists():
        sim_run.main()
    return JSONResponse({"summary": json.loads((SIM_OUT / "summary.json").read_text()),
                         "weekly": json.loads((SIM_OUT / "weekly.json").read_text())})


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


@app.get("/api/live")
def api_live():
    d = log_dir()
    q = _jsonl(d / "queue.jsonl")
    calls = _jsonl(d / "tool_calls.jsonl")
    return {"transcripts": len(list((d / "transcripts").glob("*.json"))) if (d / "transcripts").exists() else 0,
            "escalations": len(q), "unanswered": sum(1 for r in q if r.get("answered_at") is None), "tool_calls": len(calls)}


@app.post("/chat")
def chat(body: ChatIn):
    sid = body.session_id if body.session_id and SESSION_RE.fullmatch(body.session_id) else uuid.uuid4().hex[:12]
    r = run_turn_fn(body.message, system_prompt=prompt.system_prompt(), mcp_config=prompt.mcp_config(sid),
                    session_id=_claude_sessions.get(sid), model=os.environ.get("NORTHLINE_MODEL"))
    if r.session_id:
        _claude_sessions[sid] = r.session_id
    transcripts.record_turn(sid, body.message, r)
    return {"reply": r.reply, "session_id": sid, "tool_uses": r.tool_uses, "is_error": r.is_error}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("NORTHLINE_PORT", "8765")))
