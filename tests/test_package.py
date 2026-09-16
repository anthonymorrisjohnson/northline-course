import shutil
import zipfile
from pathlib import Path

from scripts.package import build

ROOT = Path(__file__).resolve().parents[1]


def test_zip_has_no_git_venv_or_logs(tmp_path):
    out = build(out=tmp_path / "z.zip")
    names = zipfile.ZipFile(out).namelist()
    assert any(n.endswith("pyproject.toml") for n in names)
    assert not any("/.git/" in n or "/.venv/" in n or "/__pycache__/" in n for n in names)
    assert not any("northline/logs/" in n and not n.endswith(".gitkeep") for n in names)
    assert all(n.startswith("northline-course/") for n in names)
    assert not any("/.superpowers/" in n for n in names)
    assert not any(n.startswith("northline-course/docs/superpowers/") for n in names)


def test_build_ignores_excluded_names_in_ancestor_path(tmp_path):
    # A checkout placed under a directory that happens to be named "dist" (or ".git", etc.)
    # must not have every file excluded: only path components *relative to root* count.
    fake_root = tmp_path / "dist" / "repo"
    fake_root.mkdir(parents=True)
    for name in ("pyproject.toml", ".mcp.json", "README.md"):
        shutil.copy(ROOT / name, fake_root / name)

    out = build(root=fake_root, out=tmp_path / "out.zip")
    names = zipfile.ZipFile(out).namelist()
    assert any(n.endswith("pyproject.toml") for n in names)
