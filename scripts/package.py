"""Build dist/northline-course.zip for attendees. No git, no venv, no logs, no generated triage files.

Author-only: this is the one script in the course that talks to git, and attendees never run it.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "dist", "briefs", ".superpowers"}
EXCLUDE_FILES = {"northline/agents/triage/decisions.json", "northline/agents/triage/prompt.md",
                 "slides/deck.pptx", ".claude/settings.local.json"}
EXCLUDE_NAMES = {".DS_Store"}
EXCLUDE_PREFIX = ("northline/logs/", "northline/agents/triage/out/", "docs/superpowers/")


def build(root: Path = ROOT, out: Path | None = None) -> Path:
    out = out or root / "dist" / "northline-course.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob("*")):
            rel_path = p.relative_to(root)
            rel = rel_path.as_posix()
            if p.is_dir() or any(part in EXCLUDE_DIRS for part in rel_path.parts) or rel in EXCLUDE_FILES:
                continue
            if p.name in EXCLUDE_NAMES:
                continue
            if rel.startswith(EXCLUDE_PREFIX) and not rel.endswith(".gitkeep"):
                continue
            z.write(p, f"northline-course/{rel}")
    return out


def dirty_files(root: Path = ROOT) -> list[str]:
    """Uncommitted paths, as `git status --porcelain` reports them. Empty when the tree is clean."""
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=str(root),
                          capture_output=True, text=True, encoding="utf-8")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


if __name__ == "__main__":
    force = "--force" in sys.argv[1:]
    dirty = dirty_files()
    if dirty and not force:
        print("Refusing to build from a dirty tree. Uncommitted:")
        for line in dirty:
            print(f"  {line}")
        print("Commit or stash them, or pass --force to package anyway.")
        raise SystemExit(1)
    print(build())
