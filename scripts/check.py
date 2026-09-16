"""Pre-flight. Run: uv run python scripts/check.py"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from northline.tools import registry

ROOT = Path(__file__).resolve().parents[1]


def write_mcp(root: Path = ROOT) -> Path:
    """Rewrite .mcp.json with absolute paths instead of ${CLAUDE_PROJECT_DIR}, and ${VAR:-default} env
    entries resolved to their defaults. Headless Claude does not expand ${CLAUDE_PROJECT_DIR} unless the
    variable happens to be set, so absolute paths remove the dependency on this laptop."""
    path = root / ".mcp.json"
    text = path.read_text()
    text = text.replace("${CLAUDE_PROJECT_DIR}", str(root))
    text = re.sub(r"\$\{\w+:-([^}]*)\}", r"\1", text)
    path.write_text(text)
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
    if shutil.which("claude"):
        print("claude " + subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip())
    else:
        print("claude not found on PATH"); ok = False
    print("\nREADY" if ok else "\nNOT READY, see above")
    print("Check-in agent + dashboard: uv run python -m northline.agent.server  ->  http://127.0.0.1:8765 and /dashboard")
    print("Prairie's analyst (MCP): this Claude Code session already has the northline tools.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
