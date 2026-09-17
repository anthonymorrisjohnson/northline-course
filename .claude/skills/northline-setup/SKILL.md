---
name: northline-setup
description: Prepare this laptop for the Northline session. Installs uv if missing, syncs dependencies, runs the checks, confirms the MCP server, and prints what to open. Works on macOS, Linux, and Windows.
disable-model-invocation: true
---

You are preparing an attendee's laptop. Do these in order. Stop with a plain-language message if a step fails; do not try workarounds that install other tools.

1. Detect the OS. Run `uv --version`. If missing:
   - macOS or Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   Then re-run `uv --version`. If it is still not found, tell the user to start a fresh session (a new chat in the Code tab, or reopen the terminal), then run /northline-setup again.
2. Run `uv sync`.
3. Run `uv run pytest -q` and report the count.
4. Run `uv run python scripts/check.py --write-mcp`. This rewrites `.mcp.json` with the absolute path to `uv` and absolute paths in place of `${CLAUDE_PROJECT_DIR}`, which headless Claude does not expand on its own.
5. Run `uv run python scripts/check.py`. If the last line is not READY, show the output and stop. If it says `claude not found`, the user needs to install Claude Code and sign in first; say so plainly and stop.
6. Tell the user to start a fresh session in this folder so Claude picks up `uv` and the rewritten `.mcp.json`. In the Claude desktop app's Code tab that means: start a new chat in the same folder. In a terminal it means: exit `claude` and run it again. If they are asked to approve the `northline` server, approve it. Then, in the new session, type `/mcp` and confirm `northline` is listed. In the Code tab it may show as "Pending approval" while the tools already work; that is fine. In a terminal it must show connected. If it shows "Failed to connect", run step 4 (`uv run python scripts/check.py --write-mcp`) again, start another fresh session, and re-check. If they declined the server earlier in a terminal, run `claude mcp reset-project-choices` and restart. If it still fails, report the exact line.
7. Finish with exactly this, filled in:
   READY: <OS>, <python version>, <claude version>, northline tools: patient <n> plan <n>
   Ask them to paste that line into the workshop group chat.
   Then two lines: "In the room you will type /northline-pm-run and /northline-deploy triage. Nothing else."

Never run git. Never modify files other than `.mcp.json`, and only through the check script. Never install anything other than uv.
