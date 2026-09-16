import shutil
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    dst = tmp_path / "data"
    shutil.copytree(ROOT / "northline" / "data", dst)
    monkeypatch.setenv("NORTHLINE_DATA_DIR", str(dst))
    return dst


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    d = tmp_path / "logs"
    d.mkdir()
    monkeypatch.setenv("NORTHLINE_LOG_DIR", str(d))
    return d


@pytest.fixture
def anyio_backend():
    return "asyncio"
