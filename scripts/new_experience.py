"""Scaffold a fresh course experience: the take-home skills and an empty tool registry,
with no corpus. See .claude/skills/new-experience/SKILL.md for the attendee-facing wrapper.
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

_SKILLS = ("setup", "brief", "tools", "agent", "pm-run", "expand", "deploy")
_SUBSTITUTE_SUFFIXES = (".py", ".md", ".html", ".json", ".toml")

_PATIENT_STUB = '"""Empty scaffold. Add {name} tool functions here and register them in registry.py."""\n'

_REGISTRY = '''"""The single list of {name} tools. Both front doors read this.

Adding a tool is one function with a docstring plus one line here. A tool with `requires`
appears only once that deployment is live in data/deployments.json; that is how a /deploy-style
skill changes what agents can do without editing Python on stage.
"""
from dataclasses import dataclass
from typing import Callable
from . import store


@dataclass(frozen=True)
class ToolSpec:
    name: str
    fn: Callable
    personas: frozenset[str]
    requires: str | None = None


def _t(fn, personas, requires=None):
    return ToolSpec(fn.__name__, fn, frozenset(personas), requires)


TOOLS: list[ToolSpec] = []


def live_deployments() -> set[str]:
    return {{d["name"] for d in store.load("deployments")}}


def select(persona: str) -> list[ToolSpec]:
    live = live_deployments()
    return [x for x in TOOLS if (persona == "all" or persona in x.personas) and (x.requires is None or x.requires in live)]
'''


def _validate_name(name: str) -> None:
    if not NAME_RE.fullmatch(name):
        raise ValueError(f"name must be a lowercase identifier (e.g. 'pharmaflow'), got {name!r}")


def _substitute(text: str, name: str) -> str:
    return (text.replace("northline", name)
                .replace("NORTHLINE", name.upper())
                .replace("Northline", name.capitalize()))


def _copy_file(src: Path, dst: Path, name: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.suffix in _SUBSTITUTE_SUFFIXES:
        dst.write_text(_substitute(src.read_text(encoding="utf-8"), name), encoding="utf-8")
    else:
        shutil.copy(src, dst)


def _copy_tree(src: Path, dst: Path, name: str) -> None:
    for p in sorted(src.rglob("*")):
        if p.is_dir() or "__pycache__" in p.parts:
            continue
        _copy_file(p, dst / p.relative_to(src), name)


def create(name: str, dest: Path, repo_root: Path | None = None) -> Path:
    """Create dest/<name>/ scaffolded from repo_root's course skills, with an empty tool
    registry and no corpus. Raises ValueError for a bad name, FileExistsError if dest/<name>
    already exists."""
    _validate_name(name)
    repo_root = repo_root or ROOT
    dest = Path(dest)
    target = dest / name
    if target.exists():
        raise FileExistsError(f"{target} already exists")
    target.mkdir(parents=True)

    # templates/
    _copy_tree(repo_root / "templates", target / "templates", name)

    # take-home skills
    for skill in _SKILLS:
        _copy_tree(repo_root / ".claude" / "skills" / skill, target / ".claude" / "skills" / skill, name)

    # top-level project files
    _copy_file(repo_root / ".mcp.json", target / ".mcp.json", name)
    _copy_file(repo_root / "pyproject.toml", target / "pyproject.toml", name)

    pkg = target / name
    (pkg / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    # tools/
    _copy_file(repo_root / "northline" / "tools" / "store.py", pkg / "tools" / "store.py", name)
    _copy_file(repo_root / "northline" / "tools" / "calllog.py", pkg / "tools" / "calllog.py", name)
    (pkg / "tools" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "tools" / "patient.py").write_text(_PATIENT_STUB.format(name=name), encoding="utf-8")
    (pkg / "tools" / "registry.py").write_text(_REGISTRY.format(name=name), encoding="utf-8")

    # mcp_server.py
    _copy_file(repo_root / "northline" / "mcp_server.py", pkg / "mcp_server.py", name)

    # agent/ (brief.md comes from the blank template, not the filled northline brief)
    _copy_tree(repo_root / "northline" / "agent", pkg / "agent", name)
    _copy_file(repo_root / "templates" / "agent-brief.md", pkg / "agent" / "brief.md", name)

    # sim/
    (pkg / "sim" / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
    (pkg / "sim" / "__init__.py").write_text("", encoding="utf-8")
    model_text = _substitute((repo_root / "northline" / "sim" / "model.py").read_text(encoding="utf-8"), name)
    model_text = model_text.replace("BASE = {", "# recalibrate BASE to your company\nBASE = {", 1)
    (pkg / "sim" / "model.py").write_text(model_text, encoding="utf-8")
    _copy_file(repo_root / "northline" / "sim" / "run.py", pkg / "sim" / "run.py", name)

    # pm/
    (pkg / "pm" / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
    (pkg / "pm" / "__init__.py").write_text("", encoding="utf-8")
    for mod in ("claude_json", "classify", "aggregate", "diagnose", "propose"):
        _copy_file(repo_root / "northline" / "pm" / f"{mod}.py", pkg / "pm" / f"{mod}.py", name)
    _copy_file(repo_root / "templates" / "taxonomy.md", pkg / "pm" / "taxonomy.md", name)

    # agents/ (empty)
    (pkg / "agents" / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
    (pkg / "agents" / "__init__.py").write_text("", encoding="utf-8")

    # data/
    (pkg / "data").mkdir(parents=True, exist_ok=True)
    (pkg / "data" / "deployments.json").write_text(json.dumps([]), encoding="utf-8")

    # logs/
    (pkg / "logs").mkdir(parents=True, exist_ok=True)
    (pkg / "logs" / ".gitkeep").write_text("", encoding="utf-8")

    # scripts/
    (target / "scripts" / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
    (target / "scripts" / "__init__.py").write_text("", encoding="utf-8")
    _copy_file(repo_root / "scripts" / "check.py", target / "scripts" / "check.py", name)

    # tests/
    (target / "tests" / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
    (target / "tests" / "__init__.py").write_text("", encoding="utf-8")
    _copy_file(repo_root / "tests" / "conftest.py", target / "tests" / "conftest.py", name)

    # README
    (target / "README.md").write_text(
        f"# {name.capitalize()}\n\n"
        f"Scaffolded from the Northline course's take-home skills: `/brief`, `/tools`, "
        f"`/agent`, `/pm-run`, `/expand`, `/deploy`, and `/setup`.\n\n"
        f"No corpus on purpose — the loop runs on your own first conversations, not generated ones.\n\n"
        f"Start with `/brief {name}`.\n",
        encoding="utf-8",
    )

    return target


if __name__ == "__main__":
    import sys
    if len(sys.argv) not in (2, 3):
        print("usage: uv run python scripts/new_experience.py <name> [dest]")
        raise SystemExit(1)
    exp_name = sys.argv[1]
    exp_dest = Path(sys.argv[2]) if len(sys.argv) == 3 else ROOT.parent
    out = create(exp_name, exp_dest, repo_root=ROOT)
    print(out)
