"""Pre-flight. Run: uv run python scripts/check.py"""
import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from northline.tools import registry

ROOT = Path(__file__).resolve().parents[1]

# Mirrors the shipped .mcp.json's "northline" server entry. write_mcp rebuilds the
# entry from this template rather than editing whatever is on disk, so it is
# idempotent and never depends on a placeholder still being present.
_MCP_SERVER_TEMPLATE = {
    "type": "stdio",
    "command": "uv",
    "args": ["run", "--directory", "${CLAUDE_PROJECT_DIR}", "python", "-m", "northline.mcp_server"],
    "env": {
        "NORTHLINE_PERSONA": "${NORTHLINE_PERSONA:-plan}",
        "NORTHLINE_LOG_DIR": "${CLAUDE_PROJECT_DIR}/northline/logs",
        "NORTHLINE_DATA_DIR": "${CLAUDE_PROJECT_DIR}/northline/data",
    },
}

_ENV_DEFAULT_RE = re.compile(r"\$\{\w+:-([^}]*)\}")


def _resolve(value, root: Path):
    """Recursively replace ${CLAUDE_PROJECT_DIR} with root.as_posix() (never str(root) -- on
    Windows that contains backslashes, which are invalid unescaped JSON) and ${VAR:-default}
    with its embedded default."""
    if isinstance(value, str):
        value = value.replace("${CLAUDE_PROJECT_DIR}", root.as_posix())
        return _ENV_DEFAULT_RE.sub(lambda m: m.group(1), value)
    if isinstance(value, list):
        return [_resolve(v, root) for v in value]
    if isinstance(value, dict):
        return {k: _resolve(v, root) for k, v in value.items()}
    return value


def write_mcp(root: Path = ROOT) -> Path:
    """Rewrite .mcp.json's "northline" server entry with absolute paths instead of
    ${CLAUDE_PROJECT_DIR}, and ${VAR:-default} env entries resolved to their defaults. Headless
    Claude does not expand ${CLAUDE_PROJECT_DIR} unless the variable happens to be set, so
    absolute paths remove the dependency on this laptop. Idempotent: every call rebuilds the
    entry from the template and the current root, so re-running it (even after the file no
    longer has the placeholder) still produces the same result."""
    path = root / ".mcp.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    entry = _resolve(copy.deepcopy(_MCP_SERVER_TEMPLATE), root)
    # Embed the absolute path to uv. Claude Code relaunched from a desktop app or a stale terminal
    # often does not have ~/.local/bin on PATH, and a bare "uv" then fails with "Failed to connect".
    uv = shutil.which("uv")
    if uv:
        entry["command"] = Path(uv).as_posix()
    config["mcpServers"]["northline"] = entry
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-mcp", action="store_true", help="rewrite .mcp.json with absolute paths")
    args = parser.parse_args()
    if args.write_mcp:
        write_mcp(ROOT)
        print("wrote .mcp.json with absolute paths")
        return 0

    ok = True
    print(f"python {sys.version.split()[0]}")
    try:
        import mcp  # noqa: F401
        print("mcp ok")
    except ImportError as e:
        print(f"mcp FAILED: {e}"); ok = False
    for persona in ("patient", "plan", "triage"):
        print(f"tools {persona}: {len(registry.select(persona))}")
    claude = shutil.which("claude")
    if claude:
        # Use the resolved path: on Windows a bare "claude" does not resolve an npm-installed claude.cmd.
        print("claude " + subprocess.run([claude, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip())
    else:
        print("claude not found on PATH. Install Claude Code and sign in, then run /setup again."); ok = False
    print("\nREADY" if ok else "\nNOT READY, see above")
    print("Check-in agent + dashboard: uv run python -m northline.agent.server  ->  http://127.0.0.1:8765 and /dashboard")
    print("Prairie's analyst (MCP): the northline tools appear in Claude Code after you restart it in this folder.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
