import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.new_experience import create

ROOT = Path(__file__).resolve().parents[1]


def test_rejects_bad_names(tmp_path):
    for bad in ("Demo", "demo-exp", "1demo", "demo exp", ""):
        with pytest.raises(ValueError):
            create(bad, tmp_path, repo_root=ROOT)


def test_refuses_to_overwrite_existing_dest(tmp_path):
    (tmp_path / "demo").mkdir()
    with pytest.raises(FileExistsError):
        create("demo", tmp_path, repo_root=ROOT)


def test_scaffold_shape(tmp_path):
    dest = create("demo_exp", tmp_path, repo_root=ROOT)

    assert dest == tmp_path / "demo_exp"
    assert (dest / "templates" / "use-case-brief.md").exists()
    assert (dest / "templates" / "agent-brief.md").exists()
    assert (dest / "templates" / "taxonomy.md").exists()
    for skill in ("setup", "brief", "tools", "agent", "pm-run", "expand", "deploy"):
        assert (dest / ".claude" / "skills" / f"demo_exp-{skill}" / "SKILL.md").exists()
    assert not (dest / ".claude" / "skills" / "generate-corpus").exists()
    assert not (dest / ".claude" / "skills" / "northline-new-experience").exists()
    assert not (dest / ".claude" / "skills" / "northline-deploy").exists()

    assert (dest / "demo_exp" / "__init__.py").exists()
    assert (dest / "demo_exp" / "tools" / "store.py").exists()
    assert (dest / "demo_exp" / "tools" / "calllog.py").exists()
    assert (dest / "demo_exp" / "tools" / "patient.py").exists()
    assert (dest / "demo_exp" / "mcp_server.py").exists()
    assert (dest / "demo_exp" / "agent" / "brief.md").exists()
    assert (dest / "demo_exp" / "agent" / "server.py").exists()
    assert (dest / "demo_exp" / "sim" / "model.py").exists()
    assert (dest / "demo_exp" / "sim" / "run.py").exists()
    assert (dest / "demo_exp" / "pm" / "classify.py").exists()
    assert (dest / "demo_exp" / "pm" / "taxonomy.md").exists()
    assert (dest / "demo_exp" / "agents" / "__init__.py").exists()
    assert (dest / "demo_exp" / "logs" / ".gitkeep").exists()
    assert (dest / "scripts" / "check.py").exists()
    assert (dest / "tests" / "conftest.py").exists()
    assert (dest / "README.md").exists()
    assert "/demo_exp-brief demo_exp" in (dest / "README.md").read_text()

    # excluded on purpose
    for excluded in ("corpus", "pm/out", "sim/out", "docs", "exercises", "slides", ".superpowers"):
        assert not (dest / excluded).exists()
        assert not (dest / "demo_exp" / excluded).exists()
    assert list((dest / "tests").glob("test_*")) == []


def test_registry_is_empty(tmp_path):
    dest = create("demo_exp", tmp_path, repo_root=ROOT)
    text = (dest / "demo_exp" / "tools" / "registry.py").read_text()
    assert "TOOLS: list[ToolSpec] = []" in text
    assert "def select(" in text and "def live_deployments(" in text


def test_deployments_json_is_empty_list(tmp_path):
    dest = create("demo_exp", tmp_path, repo_root=ROOT)
    assert json.loads((dest / "demo_exp" / "data" / "deployments.json").read_text()) == []


def test_no_northline_string_remains(tmp_path):
    dest = create("demo_exp", tmp_path, repo_root=ROOT)
    offenders = []
    for pattern in ("**/*.py", "**/.mcp.json", "**/*.toml"):
        for p in dest.glob(pattern):
            if "northline" in p.read_text().lower():
                offenders.append(str(p.relative_to(dest)))
    assert offenders == []
    assert (dest / ".mcp.json").exists()
    config = json.loads((dest / ".mcp.json").read_text())
    assert "demo_exp" in config["mcpServers"]
    pyproject = (dest / "pyproject.toml").read_text()
    assert "demo_exp" in pyproject


def test_scaffolded_skills_do_not_assume_northline_tests(tmp_path):
    dest = create("demo_exp", tmp_path, repo_root=ROOT)
    agent_skill = (dest / ".claude" / "skills" / "demo_exp-agent" / "SKILL.md").read_text()
    tools_skill = (dest / ".claude" / "skills" / "demo_exp-tools" / "SKILL.md").read_text()

    assert "demo_exp" in agent_skill
    assert "test_prompt.py" not in agent_skill

    assert "demo_exp" in tools_skill
    assert "if that file does not exist" in tools_skill


def test_model_has_recalibrate_comment(tmp_path):
    dest = create("demo_exp", tmp_path, repo_root=ROOT)
    text = (dest / "demo_exp" / "sim" / "model.py").read_text()
    assert "# recalibrate BASE to your company" in text


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed")
def test_scaffold_passes_its_own_check(tmp_path):
    dest = create("demo_exp", tmp_path, repo_root=ROOT)

    sync = subprocess.run(["uv", "sync"], cwd=dest, capture_output=True, text=True, timeout=300)
    assert sync.returncode == 0, sync.stderr

    check = subprocess.run(["uv", "run", "python", "scripts/check.py"], cwd=dest, capture_output=True, text=True, timeout=120)
    assert "Traceback" not in check.stdout and "Traceback" not in check.stderr
    assert "READY" in check.stdout  # READY or NOT READY, either is a clean run
    assert "tools patient: 0" in check.stdout
    assert "tools plan: 0" in check.stdout
