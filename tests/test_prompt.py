from northline.agent import prompt


def test_system_prompt_has_rules_and_date():
    sp = prompt.system_prompt()
    assert "## Hard rules" in sp and "escalate_to_nurse" in sp and "Today is" in sp


def test_mcp_config_patient(monkeypatch, tmp_path):
    monkeypatch.setenv("NORTHLINE_LOG_DIR", str(tmp_path))
    cfg = prompt.mcp_config("s-1")["mcpServers"]["northline"]
    assert cfg["env"]["NORTHLINE_PERSONA"] == "patient" and cfg["env"]["NORTHLINE_SESSION_ID"] == "s-1"
    assert cfg["env"]["NORTHLINE_LOG_DIR"] == str(tmp_path) and cfg["args"][-2:] == ["-m", "northline.mcp_server"]
