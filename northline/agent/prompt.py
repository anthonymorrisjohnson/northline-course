import os
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


def system_prompt() -> str:
    return (HERE / "brief.md").read_text(encoding="utf-8").rstrip() + f"\n\nToday is {date.today().isoformat()}."


def mcp_config(session_id: str) -> dict:
    return {"mcpServers": {"northline": {
        "type": "stdio", "command": "uv",
        "args": ["run", "--directory", str(REPO_ROOT), "python", "-m", "northline.mcp_server"],
        "env": {"NORTHLINE_PERSONA": "patient", "NORTHLINE_SESSION_ID": session_id,
                "NORTHLINE_LOG_DIR": os.environ.get("NORTHLINE_LOG_DIR", str(REPO_ROOT / "northline" / "logs")),
                "NORTHLINE_DATA_DIR": os.environ.get("NORTHLINE_DATA_DIR", str(REPO_ROOT / "northline" / "data"))}}}}
