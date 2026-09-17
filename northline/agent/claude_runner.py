"""One conversational turn through headless Claude Code. The controlled agent is *our* Claude Code
configuration: locked system prompt, only the Northline MCP tools, no built-ins."""
import json, shutil, subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
PREFIX = "mcp__northline__"
CLAUDE = shutil.which("claude")
NO_CLAUDE = "Claude Code (`claude`) is not on PATH; run /northline-setup"


def claude_bin() -> str:
    """The resolved `claude` executable, looked up once at import."""
    if CLAUDE is None:
        raise RuntimeError(NO_CLAUDE)
    return CLAUDE


@dataclass
class TurnResult:
    reply: str
    session_id: str
    tool_uses: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    is_error: bool = False


def build_command(message, *, system_prompt, mcp_config, session_id, model, cwd) -> list[str]:
    cmd = [claude_bin(), "-p", message, "--output-format", "stream-json", "--verbose",
           "--system-prompt", system_prompt, "--mcp-config", json.dumps(mcp_config), "--strict-mcp-config",
           "--tools", "", "--allowedTools", PREFIX + "*", "--permission-mode", "dontAsk", "--max-turns", "10"]
    if session_id:
        cmd += ["--resume", session_id]
    if model:
        cmd += ["--model", model]
    return cmd


def parse_stream(lines: Iterable[str]) -> TurnResult:
    pending, tool_uses = {}, []
    reply = session_id = ""
    cost, is_error = 0.0, False
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue
        t = d.get("type")
        if t == "assistant":
            for b in d["message"]["content"]:
                if b.get("type") == "tool_use":
                    rec = {"name": b["name"].removeprefix(PREFIX), "input": b.get("input", {}), "result": "", "is_error": False}
                    pending[b["id"]] = rec; tool_uses.append(rec)
        elif t == "user":
            for b in d["message"]["content"]:
                if b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                    c = b.get("content")
                    if isinstance(c, list):
                        c = "".join(x.get("text", "") for x in c if isinstance(x, dict))
                    pending[b["tool_use_id"]].update(result=str(c or ""), is_error=bool(b.get("is_error")))
        elif t == "result":
            reply = d.get("result") or ""
            session_id = d.get("session_id") or session_id
            cost, is_error = float(d.get("total_cost_usd") or 0), bool(d.get("is_error"))
        elif t == "system" and d.get("subtype") == "init" and not session_id:
            session_id = d.get("session_id", "")
    return TurnResult(reply, session_id, tool_uses, cost, is_error)


def run_turn(message, *, system_prompt, mcp_config, session_id=None, model=None, cwd=REPO_ROOT, runner=subprocess.run) -> TurnResult:
    cmd = build_command(message, system_prompt=system_prompt, mcp_config=mcp_config, session_id=session_id, model=model, cwd=cwd)
    try:
        proc = runner(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
                      stdin=subprocess.DEVNULL, timeout=180)
    except subprocess.TimeoutExpired:
        return TurnResult("agent error: the turn took longer than 180 s; please send that again", session_id or "", is_error=True)
    if proc.returncode != 0 and not proc.stdout.strip():
        return TurnResult(f"agent error: {getattr(proc, 'stderr', '')}".strip(), session_id or "", is_error=True)
    return parse_stream(proc.stdout.splitlines())
