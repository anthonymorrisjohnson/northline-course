import json
from types import SimpleNamespace
from northline.agent import claude_runner as cr

STREAM = [
    {"type": "system", "subtype": "init", "session_id": "sess-1"},
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "tu1", "name": "mcp__northline__log_reading",
                                                    "input": {"patient_id": "pt-1001", "kind": "bp", "value": "146/92"}}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "tu1",
                                               "content": [{"type": "text", "text": "{\"status\": \"ok\"}"}], "is_error": False}]}},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "Logged. Thanks!"}]}},
    {"type": "result", "subtype": "success", "is_error": False, "result": "Logged. Thanks!", "session_id": "sess-1", "total_cost_usd": 0.01},
]


def test_parse_stream():
    r = cr.parse_stream(json.dumps(l) for l in STREAM)
    assert r.reply == "Logged. Thanks!" and r.session_id == "sess-1" and r.cost_usd == 0.01
    assert r.tool_uses == [{"name": "log_reading", "input": {"patient_id": "pt-1001", "kind": "bp", "value": "146/92"},
                            "result": '{"status": "ok"}', "is_error": False}]


def test_build_command_lockdown(tmp_path):
    cmd = cr.build_command("hi", system_prompt="SP", mcp_config={"mcpServers": {}}, session_id=None, model=None, cwd=tmp_path)
    assert cmd[:3] == ["claude", "-p", "hi"]
    assert cmd[cmd.index("--tools") + 1] == "" and cmd[cmd.index("--allowedTools") + 1] == "mcp__northline__*"
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk" and "--strict-mcp-config" in cmd and "--resume" not in cmd


def test_build_command_resume(tmp_path):
    cmd = cr.build_command("hi", system_prompt="SP", mcp_config={}, session_id="abc", model="sonnet", cwd=tmp_path)
    assert cmd[cmd.index("--resume") + 1] == "abc" and cmd[cmd.index("--model") + 1] == "sonnet"


def test_run_turn_injected_runner(tmp_path):
    def fake(cmd, **kw):
        return SimpleNamespace(stdout="\n".join(json.dumps(l) for l in STREAM), returncode=0, stderr="")
    assert cr.run_turn("hi", system_prompt="SP", mcp_config={}, cwd=tmp_path, runner=fake).session_id == "sess-1"


def test_run_turn_error(tmp_path):
    def fake(cmd, **kw):
        return SimpleNamespace(stdout="", returncode=1, stderr="boom")
    r = cr.run_turn("hi", system_prompt="SP", mcp_config={}, cwd=tmp_path, runner=fake)
    assert r.is_error and "boom" in r.reply
