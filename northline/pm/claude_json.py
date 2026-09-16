"""LLM judgment as a function call, through headless Claude Code. No API key, no SDK."""
import json, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]


def ask_json(prompt: str, schema: dict, *, model: str = "haiku", runner=subprocess.run, cwd: Path = REPO_ROOT) -> dict:
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--json-schema", json.dumps(schema),
           "--tools", "", "--strict-mcp-config", "--no-session-persistence", "--model", model]
    proc = runner(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300)
    if not proc.stdout.strip():
        raise RuntimeError(f"claude produced no output: {getattr(proc, 'stderr', '')}")
    d = json.loads(proc.stdout)
    if d.get("is_error") or d.get("structured_output") is None:
        raise RuntimeError(f"claude failed: {d.get('result') or d.get('subtype')}")
    return d["structured_output"]


def ask_json_many(jobs, *, workers: int = 4, **kw) -> list[dict]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda j: ask_json(j[0], j[1], **kw), jobs))
