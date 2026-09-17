# Northline Course

Moving the bottleneck, live: the AI didn't fail Northline Care, the operating model around it did — and that model is a decision the room gets to make, not a fact about the technology.

## Pre-work (before the session)

1. Install the Claude desktop app and sign in with your Claude account. Use the Code tab,
   not "New project": New project runs commands in a sandbox that cannot run the course.
   (If you already use `claude` in a terminal, that works too; on Windows use the native
   installer, not npm.)
2. Download the zip: github.com/anthonymorrisjohnson/northline-course, Code, Download ZIP.
3. Unzip it into your home folder. It should be called `northline-course`.
4. In the Code tab, open the `northline-course` folder.
5. Type `/northline-setup` in the chat and follow the prompts. Stop when it prints a `READY: ...` line.
6. Paste that line into the workshop group chat.

No API key and nothing else to install: `/northline-setup` handles `uv` and the rest. The
session makes 40 to 70 model calls per laptop through your own Claude account.

## What happens in the room

You watch Northline's check-in agent work, then run the same product-management loop
a team would run on its logs: classify what patients and nurses are actually saying,
name the bottleneck it reveals, and decide what to build. You'll type two commands,
`/northline-pm-run` and `/northline-deploy triage`, and everything else is reading and answering questions
together. The deployment you build shows up live on the dashboard, alongside what it
would mean for the health plan's own numbers.

## The three surfaces

- **Check-in agent** — the SMS-style page patients use every week. Start it with
  `uv run python -m northline.agent.server`, then open `http://127.0.0.1:8765`.
- **Dashboard** — `http://127.0.0.1:8765/dashboard`, the same server. Exhibit B's
  metrics, a weekly time series, and the deployment you add during the session.
- **Prairie's analyst** — the health plan's own Claude Code session, talking to
  Northline over the same MCP tools you have open right now. No separate app.

## Take home

The skills used to build the check-in agent and its tools — `/northline-brief`, `/northline-tools`,
`/northline-agent`, `/northline-new-experience` — stay on your machine, ready to use on your own work.
Three take-home exercises in `exercises/` let you run the same loop on a case of
your own.

## Run of show

The full minute-by-minute plan, presenter notes, and fallbacks live in
[`docs/00-session-plan.md`](docs/00-session-plan.md).
