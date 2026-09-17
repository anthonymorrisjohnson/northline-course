"""Front door 2: the check-in agent as an SMS-style page. The dashboard is served here too."""
import json, os, re, uuid
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from . import claude_runner, prompt, transcripts
from northline.tools.calllog import log_dir
from northline.sim import run as sim_run

app = FastAPI(title="Northline check-in agent")
STATIC = Path(__file__).resolve().parent / "static"
SLIDES = Path(__file__).resolve().parents[2] / "slides" / "present.html"
FOLLOW = SLIDES.parent / "follow-along.html"
DECK_IMG = SLIDES.parent / "img"
SLIDES_SHELL = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
                '<style>html,body{margin:0}</style></head><body>%s</body></html>')
SIM_OUT = sim_run.OUT
run_turn_fn = claude_runner.run_turn
_claude_sessions: dict[str, str] = {}
SESSION_RE = re.compile(r"^[0-9a-f]{12}$")


if DECK_IMG.exists():
    app.mount("/img", StaticFiles(directory=DECK_IMG), name="deck-img")   # captures used by /follow


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/dashboard")
def dashboard():
    return FileResponse(STATIC / "dashboard.html")


def _deck(path: Path) -> HTMLResponse:
    """Decks are authored without a document shell, so wrap them here."""
    if not path.exists():
        return HTMLResponse("<p>That deck is not part of this folder.</p>", status_code=404)
    return HTMLResponse(SLIDES_SHELL % path.read_text(encoding="utf-8"))


@app.get("/slides")
def slides():
    """The presenter deck."""
    return _deck(SLIDES)


@app.get("/follow")
def follow():
    """The follow-along deck: what each step should look like, for the room and for anyone without a laptop."""
    return _deck(FOLLOW)


@app.get("/api/sim")
def api_sim():
    if not (SIM_OUT / "summary.json").exists():
        sim_run.main()
    return JSONResponse({"summary": json.loads((SIM_OUT / "summary.json").read_text(encoding="utf-8")),
                         "weekly": json.loads((SIM_OUT / "weekly.json").read_text(encoding="utf-8"))})


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
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
