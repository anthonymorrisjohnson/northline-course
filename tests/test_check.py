import shutil
from pathlib import Path

from scripts import check

ROOT = Path(__file__).resolve().parents[1]


def test_write_mcp_replaces_project_dir_and_env_defaults(tmp_path):
    tmp_repo = tmp_path / "repo"
    tmp_repo.mkdir()
    shutil.copy(ROOT / ".mcp.json", tmp_repo / ".mcp.json")

    result = check.write_mcp(root=tmp_repo)

    text = result.read_text()
    assert "${" not in text
    assert str(tmp_repo) in text
    assert '"plan"' in text
