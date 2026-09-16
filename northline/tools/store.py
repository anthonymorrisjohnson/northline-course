import json, os
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parents[1] / "data"

def data_dir() -> Path:
    return Path(os.environ.get("NORTHLINE_DATA_DIR", _DEFAULT))

def _p(name):
    return data_dir() / f"{name}.json"

def load(name: str) -> list[dict]:
    p = _p(name)
    return json.loads(p.read_text()) if p.exists() else []

def save(name: str, rows: list[dict]) -> None:
    _p(name).parent.mkdir(parents=True, exist_ok=True)
    _p(name).write_text(json.dumps(rows, indent=2))

def append(name: str, row: dict) -> dict:
    rows = load(name)
    rows.append(row)
    save(name, rows)
    return row
