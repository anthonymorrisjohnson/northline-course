---
name: deploy
description: Deploy an agent from an approved deployment proposal. For triage, interview the user on the four clinical-risk decisions, render the prompt, run the Exhibit E acceptance test against the nurse's key, show the misses, register the deployment, and re-run the company model. Usage /deploy triage
arguments: [agent]
---

Deploy `$agent`. Today only `triage` has a proposal (`northline/pm/out/proposals/agent-triage.md`); read it first and say in two lines where the agent sits and what it must not do.

**Decisions first. Do not write a prompt until all four are answered.** Ask one at a time. For each, offer the Northline default and say it is what Northline's product team chose; taking it is a decision and is recorded as such. Accept short answers.

1. Urgent thresholds. Default: BP at or above 180/110, glucose under 70 or over 300, always-urgent words chest, arm heavy, can't breathe, slurred, confused, stroke. Ask for their numbers and any words to add or remove.
2. Non-clinical handling. Options: `admin` (route to admin staff, default), `auto_reply` (approved content), `hold_for_morning` (stays in the nurse queue).
3. After-hours urgent rule. Options: `tell_911_and_page_on_call` (default), `tell_911_only`, `queue_for_morning`.
4. Consent. Honour "don't tell the doctor"? Default no.

Then:
5. Write `northline/agents/triage/decisions.json` in the shape `render.DEFAULTS` uses, with `chosen_by` set to `attendee` if any value differs from the default, else `northline_default`. Run `uv run python -c "import json; from northline.agents.triage import render; render.write(json.load(open('northline/agents/triage/decisions.json', encoding='utf-8')))"`.
6. Say: "Testing it on the fifteen night texts against the nurse's key. About a minute." Run `uv run python -m northline.agents.triage.acceptance` with a timeout of at least 300 seconds. Show the table it prints, unchanged. If it fails twice, say so and go on to step 8; deploy will use the committed default-decision run in `northline/agents/triage/fallback/`.
7. Point at every MISS. If there are none, say so in one line: the defaults pass the key, and the interesting table only appears when a threshold is loosened. For each trap message that missed (5, 9, 12, 13), quote the message and the nurse's note from `northline/agents/triage/nurse_key.json`. Then ask: "Do you deploy it as is, or change a decision and re-test?" If they change a decision, go back to step 5 for that decision only. Do not loop more than twice; a third time, deploy as is and say why.
8. Run `uv run python -m northline.agents.triage.deploy`. Then say: open http://127.0.0.1:8765/dashboard. If the server is not running, tell them to start it in a separate terminal window with `uv run python -m northline.agent.server` and leave that window open; do not start it from here, it would block or be killed. Tell them what to look at: the Next quarter column, the nurse response line after week 40, the "urgent cases missed" tile, and the Sign Prairie toggle.
9. Close with two lines: what their decisions did to the numbers, and the one question the board chair will ask them: "What did your triage do with 184/112?"

Never run git. Never edit Python. Never soften a MISS.
