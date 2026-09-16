import shutil
import subprocess
import zipfile
from pathlib import Path

from scripts import package
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


def test_zip_excludes_presenter_deck(tmp_path):
    out = build(out=tmp_path / "z.zip")
    names = zipfile.ZipFile(out).namelist()
    assert any(n.endswith("slides/outline.md") for n in names)
    assert not any(n.endswith("deck.pptx") for n in names)


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


def test_zip_excludes_local_settings_and_ds_store(tmp_path):
    fake_root = tmp_path / "repo"
    (fake_root / ".claude").mkdir(parents=True)
    (fake_root / "docs").mkdir()
    shutil.copy(ROOT / "pyproject.toml", fake_root / "pyproject.toml")
    (fake_root / ".claude" / "settings.local.json").write_text("{}", encoding="utf-8")
    (fake_root / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (fake_root / ".DS_Store").write_bytes(b"\x00")
    (fake_root / "docs" / ".DS_Store").write_bytes(b"\x00")

    out = build(root=fake_root, out=tmp_path / "out.zip")
    names = zipfile.ZipFile(out).namelist()

    assert "northline-course/.claude/settings.json" in names
    assert not any(n.endswith("settings.local.json") for n in names)
    assert not any(n.endswith(".DS_Store") for n in names)


def test_dirty_tree_guard_reports_uncommitted_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, text=True, check=True)
    run("git", "init", "-q")
    run("git", "config", "user.email", "a@b.c")
    run("git", "config", "user.name", "T")
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "first")

    assert package.dirty_files(repo) == []

    (repo / "a.txt").write_text("two\n", encoding="utf-8")
    assert any("a.txt" in line for line in package.dirty_files(repo))
