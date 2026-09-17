# Case crosswalk

This page is for anyone holding the paper case and wondering which file in this repo is the live version of which part.

The case document is not in this repo. It stays on paper, in the facilitator's pack, and the exercise around it is unchanged. What follows maps its parts to the things you can open on a laptop.

| Part of the case | In this repo | What it is here |
|---|---|---|
| Exhibit A | `northline/tools/plan.py`, registered in `.mcp.json` | The plan-side tools, live over MCP. Prairie's analyst calls `member_engagement`, `outcome_evidence`, `enrollment_status` and `enroll_members` from her own Claude Code; `corpus/plan/*.jsonl` holds forty sessions of her doing it. |
| Exhibit B | The dashboard's **Last quarter** column, and the first table in `northline/pm/out/report.md` | The same operations table, twice: once as the board reported it, once rebuilt from the logs. The report puts the two columns side by side so you can see they agree. |
| Exhibit C | Slide 3 of the deck | Shown on screen at the top of the session. Nothing in the repo reproduces it. |
| Exhibit D | `northline/pm/out/diagnosis.md` | The diagnosis, written by the loop from the aggregate rather than handed to the room: the bottleneck named, and the one metric to watch. |
| Exhibit E | `northline/agents/triage/exhibit_e.json` | The fifteen night texts, verbatim, with their timestamps. They are also seeded into `corpus/queue.jsonl`, so the same messages sit in the queue log the loop measures as well as in the acceptance test. They are not transcripts, so they do not appear in the classification. |
| The nurse's answer key | `northline/agents/triage/nurse_key.json` | Tier, route and a reason for all fifteen. Marked `"draft": true` with a note that a clinician should review it before use. Traps at 5, 9, 12 and 13. |
| The pocket memo | Unchanged, on paper | Read in the room at minute 12. Nothing in the repo replaces it. |
| The role cards | Unchanged, on paper | The room reads the exhibits in role exactly as before. |
| The board recommendation template | Unchanged, on paper | Filled in by hand between minutes 15 and 25, before anyone touches a laptop. |
| The threshold trap | Decision 1 in `/deploy triage` | Message 12 is 184/112 with a headache. At the default 180/110 the agent catches it. At 190/115 it does not, because the prompt applies thresholds literally. The trap is now something the room can set and watch fail. |
| The 40-hour path | The after-hours rule, decision 3 | Choosing `queue_for_morning` is the 40-hour path: message 10 at 1:48am is tiered urgent and then waits for a shift to start. The other two options page an on-call nurse or tell the patient to call 911. |
| The disengaged cohort | `patients_inactive_after_escalation` in `northline/pm/out/queue_metrics.json` | The board's 340 becomes 342 when counted from the queue log: patients who stopped responding after an escalation nobody answered. It is also a row on the dashboard and a trend chart. |
| The math table | The **Sign Prairie** toggle on the dashboard | Weeks 40 to 52, with and without the deployment the room just built. Same arithmetic, redrawn every ten seconds from the model. |

## What this does not change

Three parts of the case stay exactly as they are: the role cards, the board recommendation template, and the pocket memo. The paper exercise runs first and runs whole. The laptops come out afterwards, and what they add is the ability to watch a decision turn into a number.

## What it adds

The case asks the room to recommend something to a board. This repo lets the room build the thing it recommended, test it against a nurse's judgement, and see what its own choices did to the company — in the same hour, on the same numbers.

The two failure modes the case is about both become visible rather than argued: an under-triage shows up on the dashboard as a count of missed urgent cases, and the business-model gap shows up as revenue that does not move while the work does.
