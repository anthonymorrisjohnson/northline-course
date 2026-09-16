# Moving the Bottleneck, Live: Northline Care

Supersedes the MediBridge design of the same date. Same thesis, new story: the demo is the live version of case two in Anthony's facilitator document "Moving the bottleneck" (AfricInvest AI workshop, Tunis).

## 1. Purpose and audience

A 75-minute slot on day two of the workshop, shared with the paper case. The room is two or three C-suite people per portfolio company plus startup founders; some highly technical, some not. Everyone has Claude Code installed and logged in. Nothing else is assumed: no API key, no git, no GitHub account, no Claude Desktop.

The paper exercise from the case document stays intact: Monday email, role cards, exhibits, board recommendation, board meeting, debrief. The live loop replaces the ten-minute "fix it in Claude" triage build with a longer do-along that produces the same lesson and a company that visibly changes on a dashboard.

## 2. The lessons, in the order they land

1. **The agent worked.** Attendees see the check-in agent do its job.
2. **Same tools, other loop owner.** Prairie Health Plan's own agent pulls Northline's outcome evidence over MCP. That is how they got impressed. MCP is the tool layer; the decision is who runs the loop.
3. **The logs show who is drowning.** A product-management loop over transcripts and queue logs reproduces Exhibit B from raw data and names the bottleneck.
4. **A fix can be built in minutes, from decisions.** A triage agent is deployed from four choices the team makes.
5. **The fix is a clinical risk decision.** Exhibit E scored against the nurse key shows what each team's thresholds downgraded.
6. **The business model does not pay for what the AI surfaced.** The Prairie projection, with and without triage, on the dashboard.

## 3. Domain: Northline Care

Taken from the case, numbers preserved. Rural chronic care, 40,000 patients with hypertension and type 2 diabetes, 25 nurses before the agent and 22 after, $25 per patient per month, weekly SMS check-in agent live for nine months.

| Metric | Before the agent | Last quarter |
|---|---|---|
| Nurses | 25 | 22 |
| Engagement | 60% reached monthly | 78% respond weekly |
| Readings logged per month | 12,000 | 120,000 |
| Escalations per week | 300 | 2,400 |
| Patient-initiated messages per week | not tracked | 3,100 |
| Share sent evenings and weekends | n/a | 46% |
| Median nurse response on escalation | 4 hours | 31 hours |
| Nurse overtime hours per month | 180 | 1,150 |
| Nurse resignations last quarter | 0 | 3 |
| Patients inactive after an escalation | n/a | 340 |
| Patient satisfaction | 41 | 72 |

Three personas, each a front door or an internal agent:

- **Patients** talk to the check-in agent. Controlled, SMS-style web page. Transcripts logged.
- **Health-plan analysts** (Prairie) use the Northline MCP server from their own Claude Code. Tool calls logged.
- **Nurses** own the escalation queue. Not a chat persona; the triage agent works on their behalf once deployed.

No regional axis. The case is US-set on purpose.

## 4. Constraints

- Every LLM call goes through `claude -p` or an interactive Claude Code session. No Anthropic API key anywhere.
- No git for attendees. Distribution is a zip. No attendee-facing skill runs git. Git is an authoring tool only.
- Python >=3.12 through `uv`. `/setup` installs `uv` on macOS, Linux, and Windows.
- Attendees type two commands in the room: `/pm-run` and `/deploy triage`. Everything else is reading and answering questions.
- Every committed output exists so a laptop-less attendee can follow on paper.
- Clinical content is illustrative; the nurse answer key is the case's draft and says so.

## 5. Architecture

```
northline-course/
  README.md                        pre-work in five lines, then the map
  .mcp.json                        registers the northline MCP server
  .claude/skills/                  setup, pm-run, deploy, expand, brief, tools, agent, new-experience, generate-corpus
  northline/
    tools/                         store.py, calllog.py, patient.py, plan.py, triage.py, registry.py
    data/                          patients, plans, nurses, readings seed, deployments.json
    mcp_server.py                  front door 1 (persona from env: patient | plan | triage)
    agent/                         check-in agent: claude_runner.py, prompt.py, brief.md, transcripts.py, server.py, static/
    sim/                           model.py (weekly company model), run.py, out/weekly.json, out/summary.json
    pm/                            claude_json.py, taxonomy.md, classify.py, aggregate.py, diagnose.py, propose.py, generate_corpus.py, out/
    agents/triage/                 prompt.md (generated), decisions.json, acceptance.py, exhibit_e.json, nurse_key.json, out/
    dashboard/                     dashboard.html served by agent/server.py at /dashboard
    logs/                          transcripts/, tool_calls.jsonl, queue.jsonl (attendee-generated, not shipped)
  corpus/                          patient transcripts, plan tool-call sessions, escalation queue log, committed
  templates/                       use-case-brief, tool-spec, agent-brief, taxonomy, expansion-proposal, deployment-proposal
  docs/                            00-session-plan, 01-front-doors, 02-the-loop, 03-triage-decisions, 04-operating, 05-case-crosswalk
  exercises/                       three take-home cases
  slides/                          outline.md, deck.pptx
  scripts/                         check.py, package.py, new_experience.py
  tests/
```

### 5.1 Tool layer

Plain functions over JSON files, one registry, docstrings are what the model reads. `registry.py` tags each tool with `personas` and an optional `requires` deployment name; a tool with `requires="triage"` is exposed only once `data/deployments.json` lists triage as live. That is how `/deploy` changes what the agents can do without anyone editing Python on stage.

- Patient tools: `log_reading(patient_id, kind, value)`, `log_medication(patient_id, taken, note)`, `escalate_to_nurse(patient_id, reason, urgency)` which appends to the queue log with a timestamp, `next_checkin(patient_id)`.
- Plan tools: `member_engagement(plan_id)`, `outcome_evidence(plan_id, metric)`, `enrollment_status(member_id)`, `enroll_members(plan_id, count)`.
- Triage tools, `requires="triage"`: `pending_messages(limit)`, `tier_message(message_id, tier, rationale)`, `route_message(message_id, to, draft_reply)` where `to` is `nurse_urgent`, `nurse_routine`, `admin`, or `auto_reply`.
- Proposal-born tools such as `request_refill` and `insurance_question` do not exist at the start. `/expand` adds them; the corpus shows patients asking for them.

### 5.2 Front door 1: MCP server

`mcp_server.py` reads `NORTHLINE_PERSONA` and exposes the matching tools with call logging. `.mcp.json` defaults to `plan`, so an attendee opening Claude Code in the folder is Prairie's analyst. A presenter demo asks for engagement and outcome evidence on members; the reply is the board update's numbers, sourced from data.

### 5.3 Front door 2: check-in agent

FastAPI page at `/`, SMS-style. Each turn runs headless Claude Code with the check-in brief as system prompt, `--strict-mcp-config` pointing at the patient persona, built-in tools off, only `mcp__northline__*` allowed, `--permission-mode dontAsk`. Transcripts to `logs/transcripts/`. Escalations land in `logs/queue.jsonl` through the tool.

### 5.4 Company simulator

`sim/model.py` steps week by week over 39 weeks. State: patients, nurses, morale, deployments live per week. Per week it emits the Exhibit B metrics plus revenue and nurse cost. Calibration targets: with no deployments the "before" column; with the check-in agent from week 1 the "last quarter" column by week 39 within 10%. Deployments are entries in `data/deployments.json` with `name`, `live_from_week`, and `effects`, a dict of parameter overrides. Triage's effects come from its acceptance run: `share_routed_from_nurses`, `urgent_precision`, `urgent_recall`. A `prairie: true` flag in `run.py` projects 100,000 patients from week 40 to 52.

`sim/run.py` writes `out/weekly.json` and `out/summary.json`. The dashboard reads those.

### 5.5 Corpus

`pm/generate_corpus.py` draws events from the simulator's week-by-week escalation and message counts, tiers, and hours, then asks headless Claude to write the text. Output: 120 patient transcripts, 40 plan tool-call sessions, and `corpus/queue.jsonl` with 2,000 escalation rows carrying `created_at`, `tier`, `answered_at` (null for the unanswered), and `patient_id`. The unmet-need themes are the case's: refills, insurance, the drive to the pharmacy, diet, device errors, social contact, and the opt-out. Exhibit E's fifteen texts are seeded into the corpus verbatim.

### 5.6 The PM loop

1. **Capture**: transcripts, tool calls, queue log.
2. **Classify** (`classify.py`, headless Claude with a JSON schema): per conversation, intent, tier (`urgent_clinical`, `non_urgent_clinical`, `non_clinical`), outcome, tools used, unmet need, proposed tool, evidence quote.
3. **Aggregate** (`aggregate.py`, Python only): unmet-need candidates with counts and quotes, plus queue metrics from timestamps: escalations per week, median and p90 nurse response, after-hours share, share of nurse-queue items that are non-clinical, patients inactive after an unanswered escalation. Writes `report.md` in the Exhibit B layout with a "from logs" column next to the board's column.
4. **Diagnose** (`diagnose.py`): one page in plain words naming the bottleneck, written by headless Claude from the aggregate, saved as `diagnosis.md`. `/pm-run` withholds it until the attendee has answered the gate question.
5. **Propose** (`propose.py`): candidates of two kinds. Tool expansions fill `templates/expansion-proposal.md`. A deployment proposal fills `templates/deployment-proposal.md`: placement in the pipeline, tools it needs, the decisions a human must make, the acceptance test, the metrics it should move. The triage proposal is always among them because the queue metrics justify it.
6. **Ship**: `/expand <tool>` or `/deploy <agent>`.

### 5.7 The triage deployment

`/deploy triage` interviews the attendee on four decisions and writes `agents/triage/decisions.json`:

1. Urgent thresholds: systolic and diastolic blood pressure, glucose low and high, and the symptom words that are always urgent.
2. Non-clinical handling: route to admin staff, auto-reply from approved content, or hold for morning.
3. After-hours rule: what happens to an urgent message at 1:48am.
4. Consent: whether "don't tell the doctor" is honoured, and what the patient is told.

`prompt.md` is rendered from `decisions.json`. `acceptance.py` runs Exhibit E's fifteen messages through headless Claude with that prompt and the triage tools, compares tiers to `nurse_key.json`, prints a table with the misses highlighted (messages 5, 9, 12, 13 are the traps), and writes `out/acceptance.json` including the effects the simulator needs. The deployment is added to `data/deployments.json` only after the acceptance run completes; a low score does not block, because watching message 12 get downgraded is the lesson, but the dashboard then shows the consequence as missed urgent cases.

### 5.8 Dashboard

`dashboard.html` at `/dashboard`, no external assets. Layout: the Exhibit B table with columns Before, Last quarter, From logs, and Now; a weekly time series for escalations, nurse response, overtime, and inactive patients; a deployment timeline; a "Sign Prairie" toggle showing weeks 40 to 52 with and without triage; a small panel of live counts from `logs/`. It refreshes every ten seconds by fetching `/api/sim`. Built following the dataviz skill.

### 5.9 Skills

| Skill | In room | Purpose |
|---|---|---|
| `/setup` | pre-work | uv, sync, tests, check, MCP approval, prints the three URLs |
| `/pm-run` | yes | runs classify, aggregate, diagnose, propose; gate question before the diagnosis; asks which proposal and why, pushes back once |
| `/deploy <agent>` | yes | four decisions, render prompt, acceptance run with the miss table, register deployment, re-run sim, point at the dashboard |
| `/expand <tool>` | optional | tool from a proposal, tests first, register, no git |
| `/brief`, `/tools`, `/agent`, `/new-experience` | take-home | as before, minus git |
| `/generate-corpus` | authors | regenerate corpus from the simulator |

### 5.10 Distribution

`scripts/package.py` builds `northline-course.zip` excluding `.git`, `.venv`, `logs/*`, `__pycache__`, and `slides/deck.pptx`. Hosted at a plain URL plus USB copies. Pre-work email: download, unzip into your home folder, open Claude Code in the folder, type `/setup`, paste the green line into the group chat.

## 6. Run of show, 75 minutes

| Minutes | Room | Screen | Slides |
|---|---|---|---|
| 0 to 3 | Monday email aloud, role cards | Dashboard, "Northline ops, last quarter" | 1 title, 2 the email |
| 3 to 15 | Read exhibits in role; pocket memo at 12 | At minute 8, three minutes: Prairie analyst over MCP pulls outcome evidence | 3 the two front doors |
| 15 to 25 | Board recommendation on paper | idle | none |
| 25 to 42 | Do-along | `/pm-run`, gate question with three answers from the room, reveal, pick triage; `/deploy triage` with the four decisions voted; Exhibit E table, message 12; dashboard refresh; Prairie toggle without then with | 4 the loop, 5 the four decisions filled live |
| 42 to 50 | Board meeting, two teams, pushback | Dashboard on a team's projection | 6 pushback questions |
| 50 to 62 | Debrief themes, "where is this hiding in your market?" | Before, after agent, after triage side by side | 7 to 12 |
| 62 to 75 | Case one closer or buffer | off | 13, 14 |

## 7. Thinking gates

- `/pm-run` shows outcomes, queue metrics, and unmet needs, then asks "In one sentence, what is the problem the board doesn't see?" before revealing `diagnosis.md`. Then asks which proposal and why; if a tool is chosen over triage it replies once with the metric that choice moves and asks again.
- `/deploy triage` will not render a prompt until all four decisions are answered. The default for each is offered as "what Northline's product team chose" and taking it is logged as a decision.
- The acceptance table is shown before the dashboard updates, so the team sees its misses before it sees its improved numbers.

## 8. Slides

Fourteen: title; the email; the two front doors; the loop; the four decisions (blank, filled live); pushback questions; six theme slides (moved not automated; parameters are strategy; AI lets you pivot; a fast fix needs testing; the business model; the front-door table); case one closer; take it home. Built as `.pptx` from `slides/outline.md`, plain design.

## 9. Testing

Unit tests for every tool and the registry gating; simulator calibration tests against both Exhibit B columns; aggregate tests on a fixture queue log with known medians; acceptance scorer test on a fixture run against the nurse key; server tests with a fake runner; dashboard API test; package script test that the zip has no `.git` and no logs. Tests never call `claude`.

## 10. Success criteria

- Unzip, `/setup`, and both front doors answer within ten minutes, on macOS and Windows.
- `/pm-run` completes in under three minutes on the committed corpus and its "From logs" column matches Exhibit B within 15%.
- `/deploy triage` completes in under six minutes including the acceptance run, and two different threshold choices produce visibly different miss tables and nurse response times.
- The dashboard reflects a new deployment within one refresh.
- The 75-minute run of show holds with the paper exercise untouched.

## 11. Out of scope

Real SMS, EHR, or payer integrations. Authentication. Deployment. Any clinical decision support beyond the illustrative tiers. Case one materials beyond one closing slide.
