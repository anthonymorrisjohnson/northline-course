# Northline Course

Moving the bottleneck, live: the AI didn't fail Northline Care, the operating model around it did — and that model is a decision the room gets to make, not a fact about the technology.

## Pre-work (before the session)

1. Install the Claude desktop app and sign in. Claude Code is the **Code** tab inside it.
2. In Claude Code, click **New project**, create a new empty folder, and name it `northline`.
3. Paste this line and let it run:
   `Download github.com/anthonymorrisjohnson/northline-course as a ZIP, unzip it so the files sit directly in this folder, then delete the zip.`
4. When it says it is done, close the project and open it again, so Claude Code picks up the course's commands.
5. Type `/northline-setup` and follow the prompts. Stop when it prints a `READY: ...` line.
6. Paste that line into the workshop group chat.

No API key and nothing else to install: `/northline-setup` handles `uv` and the rest. The session
makes 40 to 70 model calls per laptop through your own Claude account. If you would
rather use a terminal: unzip the folder yourself, `cd` into it, run `claude`, then `/northline-setup`.

## What happens in the room

You watch Northline's check-in agent work, then run the same product-management loop
a team would run on its logs: classify what patients and nurses are actually saying,
name the bottleneck it reveals, and decide what to build. You'll type two commands,
`/pm-run` and `/deploy triage`, and everything else is reading and answering questions
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

The skills used to build the check-in agent and its tools — `/brief`, `/tools`,
`/agent`, `/new-experience` — stay on your machine, ready to use on your own work.
Three take-home exercises in `exercises/` let you run the same loop on a case of
your own.

## Run of show

The full minute-by-minute plan, presenter notes, and fallbacks live in
[`docs/00-session-plan.md`](docs/00-session-plan.md).
