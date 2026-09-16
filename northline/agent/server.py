"""Front door 2: the check-in agent as an SMS-style page. The dashboard is served here too."""
import os, uuid
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from . import claude_runner, prompt, transcripts

app = FastAPI(title="Northline check-in agent")
STATIC = Path(__file__).resolve().parent / "static"
run_turn_fn = claude_runner.run_turn
_claude_sessions: dict[str, str] = {}


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/chat")
def chat(body: ChatIn):
    sid = body.session_id or uuid.uuid4().hex[:12]
    r = run_turn_fn(body.message, system_prompt=prompt.system_prompt(), mcp_config=prompt.mcp_config(sid),
                    session_id=_claude_sessions.get(sid), model=os.environ.get("NORTHLINE_MODEL"))
    if r.session_id:
        _claude_sessions[sid] = r.session_id
    transcripts.record_turn(sid, body.message, r)
    return {"reply": r.reply, "session_id": sid, "tool_uses": r.tool_uses, "is_error": r.is_error}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("NORTHLINE_PORT", "8765")))
