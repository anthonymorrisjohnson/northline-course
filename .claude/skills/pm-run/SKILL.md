---
name: pm-run
description: Run the product-management loop over Northline's conversations and nurse queue: classify, aggregate, diagnose, propose. Shows the numbers first, asks what the board doesn't see, then reveals the diagnosis and the proposals.
---

You are running the loop with the attendee. The judgment steps call headless Claude Code; the counting is Python. Narrate briefly; do not paste whole files.

1. Say how many items will be classified: `uv run python -c "from northline.pm.classify import load_items, REPO_ROOT; print(len(load_items(REPO_ROOT/'corpus', REPO_ROOT/'northline'/'logs')))"`. Tell them this takes about three minutes.
2. Run `uv run python -m northline.pm.classify`. On a RuntimeError, run it once more.
3. Run `uv run python -m northline.pm.aggregate`, then `uv run python -m northline.pm.diagnose`, then `uv run python -m northline.pm.propose`. Do not show diagnosis.md yet.
4. Show, from `northline/pm/out/report.md`: the "board's numbers next to the logs" table, the tier table, and the top five candidate expansions. If any ids in `classified.jsonl` start with `live-`, find them and say which candidate the attendee's own conversation landed in, quoting their line.
5. **Gate.** Ask exactly: "In one sentence, what is the problem the board doesn't see?" Wait for the answer. Do not proceed without one. Acknowledge it in one line, without grading it.
6. Now show `northline/pm/out/diagnosis.md` in full. Then list the proposal files in `northline/pm/out/proposals/`, one line each with the metric each would move.
7. Ask: "Which proposal do you want to pursue, and why?" If they pick a tool proposal, reply once: "<tool> is <share>% of conversations. The queue metrics say the median nurse response is <h> hours. Which metric does <tool> move?" and ask again. Accept whatever they choose the second time.
8. End with the one command to run next: `/deploy triage` or `/expand <file stem>`.

Never run git. Never edit tool code here. Never skip the aggregate step even if classification looks off; the report is how you see that it is off.
