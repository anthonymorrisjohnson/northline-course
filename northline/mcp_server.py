"""Front door 1: Northline's tools over MCP. Persona from NORTHLINE_PERSONA: patient, plan, or triage."""
import os, uuid
from mcp.server import MCPServer
from northline.tools import calllog, registry


def build_server(persona: str, session_id: str) -> MCPServer:
    server = MCPServer("northline")
    for spec in registry.select(persona):
        server.add_tool(calllog.wrap(spec.fn, persona=persona, session_id=session_id),
                        name=spec.name, description=spec.fn.__doc__.strip())
    return server


if __name__ == "__main__":
    build_server(os.environ.get("NORTHLINE_PERSONA", "plan"),
                 os.environ.get("NORTHLINE_SESSION_ID") or uuid.uuid4().hex[:8]).run()
