import zipfile
from scripts.package import build


def test_zip_has_no_git_venv_or_logs(tmp_path):
    out = build(out=tmp_path / "z.zip")
    names = zipfile.ZipFile(out).namelist()
    assert any(n.endswith("pyproject.toml") for n in names)
    assert not any("/.git/" in n or "/.venv/" in n or "/__pycache__/" in n for n in names)
    assert not any("northline/logs/" in n and not n.endswith(".gitkeep") for n in names)
    assert all(n.startswith("northline-course/") for n in names)
    assert not any("/.superpowers/" in n for n in names)
    assert not any(n.startswith("northline-course/docs/superpowers/") for n in names)
