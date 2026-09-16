# One Tool Layer, Two Front Doors: MCP vs Controlled Agent

A one-hour, hands-on course for people who run or use production AI systems and are not always engineers. Delivered in Africa. Every attendee has Claude Code installed and logged in, and nothing else is assumed: no API key, no Claude Desktop, no other CLI.

## 1. Teaching thesis

**MCP is the tool layer. The real decision is who runs the loop.**

Two ways to put an AI capability in front of a customer:

- **MCP server given to the customer.** You publish tools. The customer's own agent orchestrates. You gain distribution and the customer's context. You lose the system prompt, the model, the guardrails, and the conversation. Your product signal is tool-call logs.
- **Controlled agent you host.** You own prompt, model, tools, UI, and every transcript. Costlier to build and run. The user has to come to you. You see what users asked for that you could not do.
- **The hybrid.** Build the tools once as an MCP server. Consume it from your own agent. Publish the same server externally. This is what the reference implementation shows.

Three ideas the audience should leave with:

1. Same tools, different loop owner, different product signal.
2. Geography drives which front door fits which customer.
3. Product management for an agent is a loop you can run: classify conversations, find unmet needs, propose tools, ship, repeat.

## 2. Example domain

**MediBridge** is a fictional healthcare provider network operating clinic groups in two African markets. The markets are profiles, not named countries, and each is described by what it expects, not by stereotype.

| | Region A: Southern urban network | Region B: West African clinic network |
|---|---|---|
| Modelled on | Urban private hospital group with a patient portal and medical-scheme integrations | Clinic network reaching patients through WhatsApp and mobile money |
| Language | English | French, with users who switch mid-conversation |
| Channel | Web portal, later a partner app | WhatsApp-style chat, SMS fallback for feature phones |
| Payment | Medical scheme, card | Mobile money, cash |
| Sophistication expected | Scheme eligibility checks, lab-result retrieval, prescription renewals, specialist referrals, telehealth | Reliable booking, reminders, "are my results ready", directions, family bookings |
| Regulatory framing | Strict data-protection act with health-data rules; insurer audit expectations | Data-protection act in force but clinic-level enforcement lighter; emergency-number routing matters more |
| Natural front door | MCP to the hospital group's own agent platform | Controlled agent MediBridge hosts |

Two personas. Each attendee picks one track for the hands-on portion.

- **Patient track** uses the controlled agent and works with transcripts.
- **Staff track** uses the MCP server from their own Claude Code and works with tool-call logs.

The choice of persona is also a choice of what product signal you get. That mapping is deliberate.

## 3. Constraints

- Everything runs on the attendee's laptop through Claude Code. No Anthropic API key anywhere in the repo.
- Python 3.12 with `uv`. Pre-work installs `uv` if missing; a `/setup` skill does that from inside Claude Code.
- Fresh clone to working demo in under ten minutes.
- No real clinical advice. The agent is administrative and informational only.
- No real integrations, auth, or deployment. Docs are the readable material; a slide deck carries the presenter through the hour.

## 4. Architecture

```
africinvest/
  README.md                   quickstart and the run of show in brief
  .mcp.json                   registers the MediBridge MCP server for anyone who clones
  .claude/skills/             the step templates as slash commands (section 8)
  docs/
    00-session-plan.md        60-minute run of show with timings and what attendees do
    01-tradeoff.md            MCP vs agent decision table, with the region row
    02-use-case-to-design.md  the MediBridge brief worked through, both regions
    03-live-pm.md             the PM loop, and what each front door lets you see
    04-operating.md           backlog ownership, review cadence, safety of generated tools, cost
  templates/                  clean markdown templates the skills fill in
    use-case-brief.md
    tool-spec.md
    agent-brief.md
    taxonomy.md
    expansion-proposal.md
  medibridge/                 the reference implementation
    tools/                    shared tool layer: plain Python functions over JSON data
    data/                     seed data: clinics, slots, patients, formulary, stock, claims
    mcp_server.py             front door 1: publishes the tools over MCP (stdio)
    agent/
      brief.md                the filled agent brief: system prompt, guardrails, escalation
      server.py               front door 2: FastAPI chat that runs headless Claude Code per turn
      static/index.html       one page, region toggle, portal look for A and chat look for B
    logs/
      transcripts/            one JSON file per controlled-agent conversation
      tool_calls.jsonl        every MCP tool call with args, result status, region, persona
    pm/
      taxonomy.md             the filled classification schema
      aggregate.py            deterministic: counts, per-region tables, report.md
      out/                    classified.jsonl, report.md, proposals/*.md (committed for the read track)
  corpus/                     synthetic conversations and tool logs, committed
    patient/regionA/*.json    ~50 transcripts
    patient/regionB/*.json    ~50 transcripts
    staff/regionA/*.jsonl     ~40 tool-call sessions
    staff/regionB/*.jsonl     ~40 tool-call sessions
  exercises/                  three business cases, each with a read track and a build track
  tests/
```

### 4.1 Tool layer

Plain Python functions in `medibridge/tools/`, one module per concern, no framework imports. Data lives in JSON files loaded at import and written back on mutation so a tool expansion can add a data file without a migration. Every function returns a dict with a `status` field and never raises to the caller.

Patient tools: `find_clinic`, `get_availability`, `book_appointment`, `reschedule_or_cancel`, `results_status` (ready or not ready, never values), `medication_schedule` (from the patient's own prescription record only), `escalate_to_human`.

Staff tools: `lookup_patient`, `todays_schedule`, `drug_stock`, `send_reminder`.

Region-gated tools, present in the layer and exposed only where the region config allows: `check_scheme_eligibility` (A), `mobile_money_payment_link` (B).

A `registry.py` lists every tool with name, description, JSON schema, persona, and regions. Both front doors read the registry, so adding a tool in one place adds it to both.

### 4.2 Front door 1: MCP server

`mcp_server.py` uses the official MCP Python SDK (FastMCP, stdio). It reads the registry and exposes the tools for the persona and region set by environment variables in `.mcp.json`. Every call appends a line to `logs/tool_calls.jsonl`: timestamp, session id, tool, arguments, status, region, persona, and error text if any. Attendees attach it with nothing more than opening Claude Code in the repo, since `.mcp.json` registers it.

### 4.3 Front door 2: controlled agent

`agent/server.py` is FastAPI serving one HTML page and a `/chat` endpoint. Each turn runs headless Claude Code as a subprocess:

```
claude -p --output-format json \
  --system-prompt "<brief.md plus the region block, assembled by the server>" \
  --mcp-config medibridge/agent/mcp.json \
  --allowedTools "mcp__medibridge__*" \
  --disallowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Agent" \
  --resume <session-id>
```

The system prompt is assembled from `brief.md` plus a region block. The page's region toggle switches language hints, the visual style, and which region-gated tools appear. Each conversation is written to `logs/transcripts/<session>.json`: messages, tools used, escalation flag, region, persona.

The exact flag set for restricting tools is verified during implementation against the installed Claude Code version. If `--disallowedTools` alone leaves a built-in reachable, the server also sets `--permission-mode` so anything outside the allow list is denied.

### 4.4 PM loop

LLM judgment happens inside Claude Code. Arithmetic happens in Python. That split is itself a teaching point.

1. **Capture.** Already done by the two front doors.
2. **Classify.** The `/pm-run` skill fans out subagents, each taking a batch of about ten transcripts or tool-log sessions, and writes one JSON record per conversation matching the taxonomy: intent, outcome (resolved, partial, failed, escalated), tools used, unmet need present, unmet need description, tool that would have served it, language, region, persona, one quoted line as evidence.
3. **Aggregate.** `pm/aggregate.py` validates the records, groups unmet needs by the proposed tool, and writes `report.md` with a per-region table: candidate expansion, count, share of conversations, example quotes, nearest existing tool.
4. **Propose.** The same skill asks one subagent per top candidate to fill `templates/expansion-proposal.md`: name, description, input schema, backend it needs, safety notes, regions, evidence.
5. **Ship.** `/expand <proposal>` writes the tool spec, implements the function, registers it, adds a data file if needed, runs the tests, and tells the attendee to restart the agent server. The tool then appears in both front doors.

Committed outputs in `pm/out/` let a reader follow the loop without running it.

### 4.5 Synthetic corpus

Generated once by a `/generate-corpus` skill and committed. Distributions are deliberately different by region so the two backlogs diverge on stage:

- Region A patient unmet needs: scheme eligibility, prescription renewal, lab-result values, specialist referral, telehealth booking.
- Region B patient unmet needs: mobile-money payment, SMS confirmation, French and Wolof switching, directions and transport, booking for a family member, results by SMS.
- Staff tool logs show near-misses: repeated `lookup_patient` calls with a phone number when the tool wants an ID, `drug_stock` for items not in the catalogue, `send_reminder` failing where SMS is not configured.

Each region has a small share of resolved, ordinary conversations so the classifier has to discriminate.

## 5. Session run of show

Pre-work, sent ahead: clone, open Claude Code in the folder, run `/setup`. That installs `uv` if missing, syncs dependencies, checks the MCP server loads, and prints the two URLs.

| Minutes | Attendees do | Presenter does |
|---|---|---|
| 0 to 8 | Ask their own Claude Code to book an appointment via MCP. Open the web agent, ask the same. | Names the two front doors. Shows what each logs. |
| 8 to 18 | Discussion. | Walks the tradeoff table with the region row. Asks which of their systems is which. |
| 18 to 30 | Run `/brief` on a system from their own company. Three read out their front-door decision per region. | Runs `/brief` on MediBridge for comparison. |
| 30 to 48 | Pick a track. Ask the agent, or their own Claude Code over MCP, for something it cannot do, in their own words. Run `/pm-run`. Find their own request in the backlog. Run `/expand` on it or on another proposal. Restart. Test it in both front doors. | Same on screen. Narrates the classify, aggregate, propose steps as they run. Uses a request the guardrails should refuse as a discussion point. |
| 48 to 55 | Discussion. | Operating it: who owns the backlog, review cadence, why generated tools get human review, cost per conversation. |
| 55 to 60 | Run `/new-experience` once to see a clean folder appear. | Closes on the thesis. |

## 6. Slides

A presenter deck in `slides/`, built as a `.pptx` from a markdown outline kept next to it so it can be regenerated after edits. About fifteen slides, one per beat of the run of show, plus the tradeoff table, the region table, and the loop diagram. Slides carry the framing and the discussion prompts; the live work happens in the terminal and the browser. The deck is the last thing built, after the docs and code have settled.

## 7. Readable track

Every step has a finished example a reader can follow without running anything: the filled MediBridge brief, the tool specs, the agent brief, the taxonomy, the committed classification output, the report, and the proposals. The three exercises in `exercises/` each state a business, the two-region contrast, and a read track (answer the brief on paper) and a build track (run the skills).

Exercise businesses: a pharmacy chain, a health insurer, a telemedicine startup. Each gives a different answer to the front-door question.

## 8. Skills

All live in `.claude/skills/<name>/SKILL.md` so anyone who clones the repo gets them.

| Skill | Input | Output |
|---|---|---|
| `/setup` | none | environment ready, MCP loads, URLs printed |
| `/brief` | a short interview | `templates/use-case-brief.md` filled, ending in a front-door decision per region |
| `/tools` | a filled brief | one tool spec per tool, implemented and registered |
| `/agent` | a filled brief | `agent/brief.md` with system prompt, guardrails, escalation, logging config |
| `/pm-run` | transcripts and tool logs | `pm/out/classified.jsonl`, `report.md`, `proposals/*.md` |
| `/expand <proposal>` | one proposal | spec written, tool implemented, registered, tests green |
| `/new-experience <name>` | a name | a fresh folder with empty templates and the skills, starting at step 1 |
| `/generate-corpus` | region profiles | the synthetic corpus, used once by the author |

## 9. Testing

- Unit tests for every tool function with fixture data, no LLM.
- Registry test: every tool has a schema, persona, and region set, and both front doors see the same list.
- Aggregate test: a fixture `classified.jsonl` produces a known `report.md`.
- Server smoke test with the Claude Code subprocess replaced by a fake that returns a canned JSON result.
- A `/setup` check that runs the MCP server in-process and lists its tools.

## 10. Success criteria

- Fresh clone, `/setup`, and both front doors answer a booking request within ten minutes.
- `/pm-run` finishes on the committed corpus in under five minutes on a laptop and the two regional backlogs differ visibly.
- `/expand` on a proposal produces a working tool in both front doors in under five minutes.
- A reader with no laptop can follow the loop end to end from the docs and committed outputs.
- The session fits in sixty minutes with the timings in section 5.

## 11. Out of scope

Real WhatsApp, SMS, or mobile-money integrations. Authentication. Deployment. EHR or scheme connectivity. Any clinical decision support.
