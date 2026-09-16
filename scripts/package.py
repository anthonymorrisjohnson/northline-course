"""Build dist/northline-course.zip for attendees. No git, no venv, no logs, no generated triage files."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "dist", "briefs", ".superpowers"}
EXCLUDE_FILES = {"northline/agents/triage/decisions.json", "northline/agents/triage/prompt.md"}
EXCLUDE_PREFIX = ("northline/logs/", "northline/agents/triage/out/", "docs/superpowers/")


def build(root: Path = ROOT, out: Path | None = None) -> Path:
    out = out or root / "dist" / "northline-course.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob("*")):
            rel = p.relative_to(root).as_posix()
            if p.is_dir() or any(part in EXCLUDE_DIRS for part in p.parts) or rel in EXCLUDE_FILES:
                continue
            if rel.startswith(EXCLUDE_PREFIX) and not rel.endswith(".gitkeep"):
                continue
            z.write(p, f"northline-course/{rel}")
    return out


if __name__ == "__main__":
    print(build())
