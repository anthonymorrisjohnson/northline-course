import json, pytest
from mcp import Client
from northline.mcp_server import build_server


@pytest.mark.anyio
async def test_plan_server_lists_plan_tools(data_dir, log_dir):
    async with Client(build_server(persona="plan", session_id="t1")) as c:
        names = {t.name for t in (await c.list_tools()).tools}
    assert names == {"member_engagement", "outcome_evidence", "enrollment_status", "enroll_members"}


@pytest.mark.anyio
async def test_call_logs(data_dir, log_dir):
    async with Client(build_server(persona="plan", session_id="t2")) as c:
        r = await c.call_tool("outcome_evidence", {"plan_id": "plan-prairie", "metric": "escalations"})
    assert r.structured_content["value"] == 2400
    assert json.loads((log_dir / "tool_calls.jsonl").read_text().strip())["session_id"] == "t2"
