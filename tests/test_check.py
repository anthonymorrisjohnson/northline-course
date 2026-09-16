import json
import shutil
from pathlib import Path

from scripts import check

ROOT = Path(__file__).resolve().parents[1]


def _tmp_repo(tmp_path) -> Path:
    tmp_repo = tmp_path / "repo"
    tmp_repo.mkdir()
    shutil.copy(ROOT / ".mcp.json", tmp_repo / ".mcp.json")
    return tmp_repo


def test_write_mcp_replaces_project_dir_and_env_defaults(tmp_path):
    tmp_repo = _tmp_repo(tmp_path)

    result = check.write_mcp(root=tmp_repo)

    text = result.read_text()
    assert "${" not in text
    assert tmp_repo.as_posix() in text
    assert '"plan"' in text


def test_write_mcp_is_idempotent(tmp_path):
    tmp_repo = _tmp_repo(tmp_path)

    first = check.write_mcp(root=tmp_repo).read_text()
    json.loads(first)  # valid JSON after the first run
    second = check.write_mcp(root=tmp_repo).read_text()

    assert json.loads(second)  # still valid JSON on a second, placeholder-free run
    assert second == first


def test_write_mcp_uses_posix_paths_for_windows_safety(tmp_path):
    tmp_repo = _tmp_repo(tmp_path)

    result = check.write_mcp(root=tmp_repo)
    text = result.read_text()
    config = json.loads(text)  # raises if backslashes broke JSON, as they would on Windows

    args = config["mcpServers"]["northline"]["args"]
    assert tmp_repo.as_posix() in args
    assert "\\" not in text
