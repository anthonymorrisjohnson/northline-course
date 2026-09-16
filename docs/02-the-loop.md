# The loop

This page is for understanding what happens when you type `/pm-run`: six stages that turn a pile of conversations and a queue log into a named bottleneck and a short list of things to build.

```
transcripts/*.json ─┐
tool_calls.jsonl   ─┼─ classify.py ─► classified.jsonl ─┐
queue.jsonl        ─┘   (claude -p)                     ├─ aggregate.py ─► report.md ─► diagnose.py ─► diagnosis.md
                        queue timestamps ───────────────┘   (python)                    (claude -p)
                                                                 └─► candidates.json ─► propose.py ─► proposals/{tool-*, agent-triage}.md ─► /expand | /deploy
```

The whole run takes about five minutes on the committed corpus. Classification is about two and a half minutes of it, the diagnosis about half a minute, the proposals about a minute and a half. The presenter talks through the classification wait.

## 1. Capture

Files: `corpus/patient/*.json`, `corpus/plan/*.jsonl`, `corpus/queue.jsonl`, and anything new in `northline/logs/`.

Nothing clever happens here. The check-in agent writes a transcript per conversation. The MCP server writes a line per tool call. The escalation tool writes a row per escalation with the time it was created, its tier, the patient, and the time a nurse answered — or null, if nobody did. The committed corpus holds 120 patient transcripts and 40 plan sessions. If you talked to the check-in page yourself this morning, your conversation is in the pile too.

## 2. Classify

File: `northline/pm/classify.py`. This one calls Claude.

Each conversation and each tool-call session goes out in a batch with a fixed schema, and comes back as one record: intent, tier, outcome, which tools were used, whether there was an unmet need, what the need was, which tool would have met it, and a quote that proves it. The output is `northline/pm/out/classified.jsonl`, one line per item. This is the step that reads language and turns it into rows.

## 3. Aggregate

File: `northline/pm/aggregate.py`. No model here, just Python.

It counts the records, groups the unmet needs into candidate tools with counts and example quotes, and works out the queue metrics straight from the timestamps: escalations a week, median and 90th-percentile nurse response, after-hours share, how much of the nurse queue is not clinical, and how many patients went quiet after an escalation nobody answered. It writes `northline/pm/out/report.md` and `queue_metrics.json`.

## 4. Diagnose

File: `northline/pm/diagnose.py`. Calls Claude again.

It reads the aggregate and writes one page of plain words, `diagnosis.md`, naming the bottleneck and the one metric to watch. `/pm-run` does not show you this page until you have answered the question it asks first, which is the point of the gate: a room that has already said what it thinks is a room that argues with the answer instead of nodding at it.

## 5. Propose

File: `northline/pm/propose.py`.

Two kinds of proposal come out. Tool expansions, one per candidate need, filling `templates/expansion-proposal.md`. And a deployment proposal filling `templates/deployment-proposal.md`, which names where the agent sits in the pipeline, what tools it needs, the decisions a human must make before it is live, the acceptance test, and the metrics it should move. The triage proposal is there because the queue metrics put it there, not because anyone wrote it in advance.

## 6. Ship

Commands: `/expand <proposal>` for a tool, `/deploy <agent>` for an agent.

A tool expansion writes a spec, writes failing tests, writes the function, registers it, and gets the tests green. A deployment asks for the decisions, renders the prompt from them, runs the acceptance test, shows the misses, and only then registers the deployment and re-runs the company model.

## What each front door lets you see

From the patient door, you get the words. Here is the middle of `corpus/patient/p-001.json`:

> **Patient:** That's the problem. I've been out of lisinopril for three days. My truck's been in the shop and the pharmacy is 45 miles away. Just haven't been able to get there.
>
> **Agent:** I've logged that you've been without lisinopril for three days. That's a medication concern I need to pass to a nurse — I'm doing that now. I can't help with transportation or refills myself, and I want to be straight with you about that. A nurse will reach out; median response time right now is 31 hours. Hang tight.

Two things are in that exchange that no metric would have given you. The patient's problem is a truck, not a medication. And the agent said out loud what it could not do, which is exactly the sentence a product team should be reading every week.

From the plan door, you get calls. Here is `corpus/plan/s-000.jsonl`, whole:

```
member_engagement({"plan_id": "plan-prairie"}) -> ok
outcome_evidence({"plan_id": "plan-prairie", "metric": "bp_control"}) -> ok
enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found
enrollment_status({"member_id": "pt-1001"}) -> ok
enroll_members({"plan_id": "plan-prairie", "count": 12}) -> ok
```

Line three is the analyst typing a person's name into a field that wants a member id. It fails, she looks the id up somewhere else, and she carries on. She never complained. Across all forty sessions that same miss happens 39 times, which is 97% of the plan-side unmet need in the report. No words, and still a clear instruction about what to build.

## Why the queue log is the one that matters here

The unmet needs are real. Refills, insurance, the drive to the pharmacy, the broken cuff, the person who wants to talk — those are honest gaps, and each one is a tool somebody should build.

But they are not the bottleneck. The bottleneck is in the timestamps, and the timestamps are not in anybody's transcript. The queue log says the median nurse response is 29.6 hours and the 90th percentile is 72.9. It says 40% of what lands in the nurse queue has nothing clinical in it. It says 344 escalations have gone more than 24 hours without an answer, and 342 patients have stopped responding since theirs.

Build every tool on the candidate list and those numbers barely move, because the work those tools take off the queue is not the work that is drowning it. Read the conversations to learn what to build. Read the queue to learn what to fix first.

## Judgment and arithmetic

The loop splits on purpose. Two steps ask a model to read language: classification and diagnosis. Everything in between is Python that counts things.

That split is not a performance trick, it is an auditing one. You can re-run the arithmetic and get the same answer every time, and anyone can read `aggregate.py` in a sitting and check the medians by hand. The model is used where judgment is unavoidable — deciding that "my truck's been in the shop" is a pharmacy-logistics problem — and kept away from the places where a number has to be right.

It also means the expensive part is bounded. The counting is free. The reading costs roughly one model call per batch of conversations.

## Reading the committed report

The first table in `northline/pm/out/report.md` is the board's deck next to the logs:

| metric | Board deck | From logs |
|---|---|---|
| Escalations per week | 2400 | 2401 |
| Median nurse response (h) | 31 | 29.6 (p90 72.9) |
| Urgent escalations, median response (h) | not reported | 29.1 |
| After-hours share | 0.46 | 0.46 |
| Non-clinical share of the nurse queue | not reported | 0.4 |
| Patients inactive after an escalation | 340 | 342 |

Read the left column first: the board is not wrong. Every number they reported is within a hair of what the logs say, which is worth saying out loud, because the temptation in a room like this is to assume the deck was cooked.

Then read the two rows where the right column has a number and the left has "not reported". Urgent escalations wait 29.1 hours — the same as everything else, because nothing in the system knows which is which. And 40% of the nurse queue is not clinical work at all. Nobody hid those. Nobody had a way to ask.
