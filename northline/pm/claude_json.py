"""LLM judgment as a function call, through headless Claude Code. No API key, no SDK."""
import json, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE = shutil.which("claude")
NO_CLAUDE = "Claude Code (`claude`) is not on PATH; run /setup"


def claude_bin() -> str:
    """The resolved `claude` executable. Resolved once at import so a PATH change mid-run cannot split a batch."""
    if CLAUDE is None:
        raise RuntimeError(NO_CLAUDE)
    return CLAUDE


def ask_json(prompt: str, schema: dict, *, model: str = "haiku", runner=subprocess.run, cwd: Path = REPO_ROOT) -> dict:
    cmd = [claude_bin(), "-p", prompt, "--output-format", "json", "--json-schema", json.dumps(schema),
           "--tools", "", "--strict-mcp-config", "--no-session-persistence", "--model", model]
    try:
        # encoding="utf-8": claude prints UTF-8; without this Windows decodes it as cp1252 and curly quotes
        # become mojibake or raise. stdin=DEVNULL: otherwise claude waits 3 s for piped stdin on every call.
        proc = runner(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
                      stdin=subprocess.DEVNULL, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("claude timed out after 300 s") from exc
    if not proc.stdout.strip():
        raise RuntimeError(f"claude produced no output: {getattr(proc, 'stderr', '')}")
    try:
        d = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"claude returned non-JSON output: {proc.stdout[:200]}") from exc
    if d.get("is_error") or d.get("structured_output") is None:
        raise RuntimeError(f"claude failed: {d.get('result') or d.get('subtype')}")
    return d["structured_output"]


def ask_json_many(jobs, *, workers: int = 4, retries: int = 1, **kw) -> list[dict]:
    def _attempt(job):
        prompt, schema = job
        last_exc = None
        for _ in range(retries + 1):
            try:
                return ask_json(prompt, schema, **kw)
            except RuntimeError as exc:
                last_exc = exc
        raise last_exc

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_attempt, jobs))
