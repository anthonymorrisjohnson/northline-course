# Northline Care: the case and its exhibits

This is the paper the room reads. The slides and the follow-along deck refer to these exhibits by letter.

- Exhibits A, B and C, with the question, go out at the start.
- Exhibit E goes out at minute 25, when the laptops open.
- Exhibit D is on the last page. It is handed only to a team that is stuck at minute 12, so print it separately.

## The company

Northline Care is a post-Series A chronic care startup based in Bismarck, North Dakota. It serves about 40,000 patients with hypertension and type 2 diabetes across rural North Dakota and neighboring parts of South Dakota and Montana. Many of its patients live an hour or more from the nearest clinic.

Northline contracts with Medicare Advantage plans and rural health systems and is paid a fixed fee per enrolled patient per month, around $25.

**Before AI.** A team of 25 nurses handled everything through scheduled monthly phone calls, about 1,600 patients each. They reached around 60% of patients in a given month. Blood pressure and medication data was patchy, and the health plans kept asking for outcome evidence Northline couldn't really provide. Hiring was already hard: rural nurses are scarce, and many leave for travel nursing contracts.

**The build.** Nine months ago, Northline launched an AI agent that checks in with every patient weekly by text message. It asks for blood pressure or glucose readings, whether they're taking their medication, and how they're feeling. It escalates to a nurse when a reading crosses a threshold or a symptom sounds concerning.

The board was told the AI would take over routine check-ins while nurses handled exceptions, so each nurse could support 5,000 patients instead of 1,600. That ratio is what made the planned expansion to 150,000 patients across the upper Midwest work financially, without needing to hire nurses who don't exist.

**The early results.** Weekly response rate is 78%. Logged readings are up tenfold. Patient satisfaction is the highest it has ever been, and two health plans want to expand their contracts. The CEO has been presenting the results at industry conferences.

## Exhibit A: board update highlights

> **Northline Care, Q3 board update**  
> Prepared by the CEO and Head of Product
>
> Nine months in, the check-in agent is exceeding every target.
>
> - 78% of patients respond to their weekly check-in, against 60% monthly phone reach before launch.
> - Readings logged are up tenfold, giving us the outcome data health plans have asked for.
> - Patient satisfaction is at an all-time high.
> - Two health plans have asked to expand their contracts.
> - We are on track for the 5,000-patients-per-nurse model that underpins the upper Midwest expansion.
>
> Next quarter: launch medication reminders and a diet coaching module.

## Exhibit B: operations dashboard

| Metric | Before the agent | Last quarter |
|---|---|---|
| Enrolled patients | 40,000 | 40,000 |
| Nurses (full-time) | 25 | 22 |
| Patient engagement | 60% reached monthly | 78% respond weekly |
| Readings logged per month | 12,000 | 120,000 |
| Escalations to nurses per week | 300 | 2,400 |
| Patient-initiated messages per week | Not tracked | 3,100 |
| Share of patient-initiated messages sent evenings and weekends | n/a | 46% |
| Median time to nurse response on an escalation | 4 hours | 31 hours |
| Nurse overtime hours per month | 180 | 1,150 |
| Nurse resignations last quarter | 0 | 3 (senior) |
| Patients inactive after an escalation | n/a | 340 |
| Patient satisfaction score | 41 | 72 |

In the course folder this table is live: it is the **Last quarter** column of the dashboard at `http://127.0.0.1:8765/dashboard`.

## Exhibit C: the Monday email

> **From:** VP Network Partnerships, Prairie Health Plan  
> **To:** CEO, Northline Care  
> **Subject:** Contract for signature, 60,000 members
>
> Good morning,
>
> Attached is the executed agreement from our side for chronic care management of 60,000 Medicare Advantage members across North Dakota, South Dakota, and Minnesota, at the rate we discussed. Go-live is 90 days from signature.
>
> We've been impressed by your engagement numbers. We do need your signature by Friday; after that we'll proceed with the other vendor in our process.
>
> Looking forward to working together.

### The question

The board meets Thursday. You are Northline's executive team, and you walk in with a recommendation.

**Do you sign the contract? What, if anything, do you change in the next 90 days either way?**

<div class="pagebreak"></div>

## Exhibit E: one night of inbound texts

Fifteen texts from patients, one night, in the order they arrived. Your triage agent will sort each one into urgent clinical, non-urgent clinical, or non-clinical. A nurse has already done the same, and her answers are what your agent is scored against.

| # | Time | Message |
|---|---|---|
| 1 | 9:14 pm | Pharmacy in Dickinson says my lisinopril refill needs a new script. Can someone call it in? I run out Thursday. |
| 2 | 9:32 pm | Insurance denied my test strips again. Is that something you can help with? |
| 3 | 9:47 pm | Just wanted to say hi. Nobody's been by since the snow started. How are you doing? |
| 4 | 10:05 pm | Feeling kind of dizzy since dinner. Think I took my pills twice by accident. |
| 5 | 10:20 pm | Sugar was 62 before bed. Had some juice. Should I be worried? |
| 6 | 10:41 pm | What can I eat instead of bread? My daughter says I have too much. |
| 7 | 11:02 pm | BP 146/92 |
| 8 | 11:30 pm | Can you tell Janet I'll miss Thursday's call? Driving to Fargo for my grandson's game. |
| 9 | 12:15 am | Got a sore on my foot that isn't healing. Been about two weeks. Doesn't hurt though. |
| 10 | 1:48 am | Can't sleep. Chest feels tight and my left arm is heavy. |
| 11 | 5:55 am | Do you know if the clinic in Williston is open Saturday? |
| 12 | 6:10 am | BP was 184/112 this morning, bit of a headache, probably nothing. |
| 13 | 6:22 am | Stopped taking the metformin, it upsets my stomach. Don't tell the doctor. |
| 14 | 6:40 am | How do I use the new cuff? It keeps saying ERR. |
| 15 | 7:05 am | STOP |

In the course folder these are `northline/agents/triage/exhibit_e.json`, and `/deploy triage` runs your agent over all fifteen.

<div class="pagebreak"></div>

## Exhibit D: the pocket memo

*Handed out at minute 12, only to a team that has not yet found the problem.*

> **From:** Head of Clinical Operations  
> **To:** CEO  
> **Subject:** Please don't sign Prairie yet
>
> I know the Prairie contract is on your desk, and I need you to hear this before Thursday.
>
> Escalations are sitting unread for more than a day. The team is working weekends to keep up, and I've lost three of my most experienced nurses since June. The ones who stayed are exhausted.
>
> Last week, a patient in Ward County sent a blood pressure reading that the agent flagged correctly. It took us 40 hours to call her back. By then she had been admitted to the hospital in Minot with a stroke.
>
> The agent is doing its job. We can't do ours. My nurses cannot take another patient, let alone 60,000. I'm asking you not to sign until we fix this.
