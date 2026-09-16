# Exercise 3: a telemedicine startup

This exercise is for the case where both doors are right, and for recognising a bottleneck you have already watched happen once.

## The business

An eighteen-month-old telemedicine company with 60,000 patients and 40 clinicians, doing async messaging and video visits for primary care. Patients message whenever they like; a clinician answers, usually the same day, sometimes with a video visit. Growth comes from two places: direct sign-ups, and eleven employer benefits platforms that resell the service to their own customers and want evidence it is being used. An intake agent already collects symptoms before a visit, and it works — clinicians say the notes are better than what they used to get, and visits start faster. The founders are raising a Series B on engagement numbers and are about to sign three more platform partners.

## Two personas

**Patients.** They message from a phone, at night, about things that worry them. The channel is text. What they write is clinical information and it is also the only product research the company has.

**Benefits platform partners.** They resell the service and need utilisation, engagement and outcome evidence to justify it to their own customers. They have analysts. Several of them already run an AI assistant over their benefits data and would rather query than receive a PDF.

## Where will the bottleneck move?

Write one sentence before you read on: **when intake gets good enough that more patients start conversations, whose queue grows?**

You have seen this one. Try to answer it without looking at the Northline numbers, then go and look.

## Read track

1. **Front doors.** For each persona, which door — the tools handed to their own agent, or an agent you build and host? Name what you give up in each case.
2. **First three tools.** Which three ship first, and which persona is each one for?
3. **The bottleneck metric.** What is the one number that shows the bottleneck has moved, and who reads it every week?

## Build track

```
/new-experience telemed
cd ../telemed && uv sync && uv run python scripts/check.py
```

Then, in a Claude Code session in the new folder:

1. `/brief telemed` — answer as the founders. Section 5 is the whole exercise; write the clinician queue into it before the tool asks you to.
2. `/tools telemed` — it builds the tools your brief named, tests first, one at a time. Notice that the patient tools and the partner tools sit in the same registry.
3. `/agent telemed` — it writes the agent brief and offers to install it as the live prompt. Say yes.
4. Start the page: `uv run python -m telemed.agent.server`, then open `http://127.0.0.1:8765`.
5. Have five conversations as a patient. Send one of them at 2am in your head and write it the way someone would actually write it. Send one that should go straight to a clinician.
6. `/pm-run` on your own five conversations, and read the unmet-need list against your own brief's section 7.

## Answer sketch

*One defensible answer, not the answer.*

**The bottleneck moves to clinicians, exactly as it did at Northline.** Better intake means more conversations started, more of them out of hours, and more of them reaching a person. Forty clinicians is a fixed number that changes slowly and gets smaller when it is overworked. At Northline the equivalent move took median response from 4 hours to 29.6, added a thousand hours of overtime a month, and lost three nurses in a quarter, and none of it appeared in the engagement numbers the board was reading.

**Both doors, one tool layer.** Patients get a controlled agent: the channel is text, the content is clinical, the guardrails have to be yours end to end, and their words are the only product research you have. Partners get MCP: they have analysts, they want evidence in their own tools, and tool calls tell you which cuts they ask for and which ones fail. The same functions serve both — that is the hybrid, and it is why the front-door question is per persona and not per company.

**First three tools:** `log_symptoms`, `book_visit`, `escalate_to_clinician` for patients; then `utilisation_summary` for partners as soon as the second platform asks for the same spreadsheet. Note that `escalate_to_clinician` is the tool that feeds the bottleneck, so it should log a timestamp at creation and another when a clinician answers, from the day it ships. Northline's whole diagnosis came out of those two timestamps.

**The metric:** median hours from patient message to clinician reply, split by whether the message arrived inside clinic hours. The clinical lead reads it weekly, and it belongs on the same page as the engagement chart the Series B deck uses, because engagement is what pushes it up. Add a second number as soon as you have it: how many patients stop messaging after a reply took too long. At Northline that was 342 people, and nobody was counting them until the loop did.
