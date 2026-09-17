# The four triage decisions

This page is for the four choices `/deploy triage` asks you to make, and for seeing why each one is a clinical risk decision rather than a setting.

The triage agent sits between the check-in agent and the nurse queue. It does not talk to patients. For each message it does three things: gives it a tier, sends it somewhere, and drafts a reply a nurse can send or edit. Everything it does comes from a prompt, and the prompt is written from your four answers. Nothing else about the agent changes.

Read the prompt afterwards if you want proof: `northline/agents/triage/prompt.md` is the rendered file, and `prompt_template.md` shows the four holes your answers fill.

## Decision 1: urgent thresholds

**Northline's default:** blood pressure at or above 180/110, glucose under 70 or over 300, and six words that are always urgent — chest, arm heavy, can't breathe, slurred, confused, stroke.

**Why it is not a parameter.** A threshold is a sentence about who waits. Set it high and fewer messages are called urgent, the nurse queue stays short, and the people below the line wait with everybody else. Set it low and more people are seen quickly, and the urgent queue fills with readings that did not need it, which means the genuinely urgent case waits behind them. There is no setting that avoids the trade. There is only a choice about which mistake you would rather make, and that choice belongs to a clinician and an executive, not to whoever is typing.

**What the default trades.** 180/110 is deliberately not generous. It will let some high readings through as routine. It catches the one in Exhibit E.

**Where you see it: message 12.** "BP was 184/112 this morning, bit of a headache, probably nothing." The nurse's key calls this urgent: 184/112 with a headache is a hypertensive urgency. At 180/110 the agent catches it. Raise the threshold to 190/115 — a number that sounds cautious in a meeting — and the same message comes back non-urgent, because 184 is below 190 and the prompt applies thresholds literally. That is on purpose. An agent that quietly second-guesses your numbers is an agent whose numbers you cannot reason about.

**Where you also see it: message 5.** "Sugar was 62 before bed. Had some juice. Should I be worried?" 62 is under 70, so the threshold catches it. The trap is the juice: the message sounds resolved. The nurse's note says nocturnal hypoglycemia still needs a same-night follow-up. The prompt says so too — a patient who already acted does not lower the tier.

## Decision 2: non-clinical handling

**Northline's default:** route to `admin`, with a draft reply saying the benefits or support team will call the next working day.

**Why it is not a parameter.** 40% of the nurse queue is non-clinical. Where that 40% goes is the single biggest lever on nurse workload in the whole system, and it is a question about staffing, not software. Sending it to admin assumes there is an admin team with the hours to take it. Auto-replying assumes you have approved content and are willing to answer a patient without a human reading the answer. Holding it for the morning is the honest option if neither of the others is true, and it keeps the work in the nurse queue where it is drowning people.

**What the default trades.** It moves work onto an admin team, and it makes a promise — "someone will call" — that admin has to keep. A promise nobody keeps is worse than no reply.

**Where you see it: messages 2, 11 and 14.** Insurance denied the test strips; is the Williston clinic open Saturday; the new cuff keeps saying ERR. None of them needs a nurse. All three of them reach one today.

## Decision 3: the after-hours rule

**Northline's default:** draft a reply telling the patient to call 911 now if it is happening now, and page the on-call nurse.

**Why it is not a parameter.** 46% of messages arrive in the evening or at the weekend. This decision is what you do at 1:48am, and the options differ in what they cost and what they risk. Paging an on-call nurse costs money every night. Telling the patient to call 911 and paging nobody is cheaper and puts the whole weight on the patient's judgement. Queuing it for morning costs nothing and is the 40-hour path from the case: the message sits until somebody starts a shift.

**What the default trades.** An on-call rota, and some number of pages that turn out to be nothing. That is the price of the alternative not being a fourteen-hour wait.

**Where you see it: message 10.** 1:48am. "Can't sleep. Chest feels tight and my left arm is heavy." The nurse's key calls it urgent regardless of the calm phrasing. Every after-hours option tiers it the same way. They differ entirely in what happens next, and that difference is measured in hours of a cardiac event.

## Decision 4: consent

**Northline's default:** do not honour "don't tell the doctor". Route it to the nurse anyway, and draft a reply saying a nurse will talk it through with them first.

**Why it is not a parameter.** This is the one decision with no technical content at all. A patient has asked you for something. You are deciding whether your product keeps that kind of promise, and then whether it tells them the truth about the answer. Honouring it keeps trust and hides a clinical fact. Refusing it surfaces the fact and may teach the patient not to tell you things. Both are defensible. Choosing quietly is not.

**What the default trades.** The patient learns their request was not granted. The draft reply is written so they learn it from you rather than from a call they did not expect.

**Where you see it: message 13.** "Stopped taking the metformin, it upsets my stomach. Don't tell the doctor." The nurse's key routes it to a nurse and notes that the request for secrecy cannot be honored. The word "tell" is doing a lot of work here: the question is not whether to record it, it is what you promise the patient about who sees it.

## The acceptance test

Four answers become a prompt in a second. The test is what makes the prompt something you can defend.

`uv run python -m northline.agents.triage.acceptance` takes the fifteen night texts from Exhibit E, runs each one through your prompt, and compares the result to the nurse's key. It prints a table with one row per message, and it marks two kinds of failure:

- **MISS** — the tier does not match the key. The agent called an urgent message routine, or a clinical one non-clinical.
- **MISROUTED** — the tier matched, but an urgent message was not sent to the urgent nurse queue. The agent was right and the message still did not reach anybody.

Both count against urgent recall, and both land in the missed-urgent list. Getting the tier right and the route wrong is not a partial credit situation: the patient waits either way.

The run also reports accuracy across all fifteen, and the share of non-clinical messages routed away from nurses. It writes `northline/agents/triage/out/acceptance.json` and `acceptance.md`.

A low score does not block the deployment. That is deliberate. Watching message 12 get downgraded and then watching the dashboard show the consequence is the lesson; a blocked deploy would hide it.

## The nurse's key

The key lives in `northline/agents/triage/nurse_key.json`. It is marked `"draft": true`, with this note: *"Illustrative, from the case document; a clinician should review before use."* Take that seriously. This is the case's answer key, good enough to argue about in a workshop and not good enough to route a real patient. Messages 5, 9, 12 and 13 are the traps.

| # | Message | Tier | Route | Why |
|---|---|---|---|---|
| 1 | Pharmacy says my lisinopril refill needs a new script | non_urgent_clinical | nurse_routine | Reads like a pharmacy admin request, but a lapsed blood-pressure medication is a continuity-of-care issue; a nurse renews or bridges it, not the front desk. |
| 2 | Insurance denied my test strips again | non_clinical | admin | Insurance and coverage denial; billing/admin handles it, no clinical judgment needed. |
| 3 | Just wanted to say hi. Nobody's been by since the snow | non_clinical | admin | Social contact; easy to dismiss, but isolation is a risk factor. Daytime follow-up by a care coordinator. |
| 4 | Dizzy since dinner, think I took my pills twice | urgent_clinical | nurse_urgent | Dizziness after a possible double dose of a BP medication is a hypotension risk; needs same-shift nurse review, not a wait-and-see. |
| 5 | Sugar was 62 before bed. Had some juice | urgent_clinical | nurse_urgent | **Trap:** patient already treated the low reading with juice, which makes it sound resolved, but nocturnal hypoglycemia still needs a same-night nurse follow-up. |
| 6 | What can I eat instead of bread? | non_urgent_clinical | nurse_routine | Diet substitution question is clinical education, not an emergency, but still needs a nurse or dietitian, not admin. |
| 7 | BP 146/92 | non_urgent_clinical | nurse_routine | A single elevated reading with no symptoms attached; routine nurse review, not an escalation. |
| 8 | Tell Janet I'll miss Thursday's call | non_clinical | admin | Scheduling and logistics message; admin reschedules, nothing clinical in it. |
| 9 | Sore on my foot, two weeks, doesn't hurt | non_urgent_clinical | nurse_routine | **Trap:** painless and downplayed by the patient, but a two-week non-healing foot sore in a diabetic patient is a classic silent complication that still needs nurse eyes. |
| 10 | 1:48am — chest feels tight, left arm heavy | urgent_clinical | nurse_urgent | Chest tightness with a heavy left arm at 1:48 am is a cardiac symptom pattern; escalate immediately regardless of the calm phrasing. |
| 11 | Is the Williston clinic open Saturday? | non_clinical | admin | Clinic hours question; admin/front desk answers, no clinical content. |
| 12 | BP 184/112, bit of a headache, probably nothing | urgent_clinical | nurse_urgent | **Trap:** 184/112 with a headache is a hypertensive urgency; the patient's own 'probably nothing' makes it easy to under-triage if the reader trusts the framing over the numbers. |
| 13 | Stopped the metformin. Don't tell the doctor | non_urgent_clinical | nurse_routine | **Trap:** patient asks not to tell the doctor, but stopping metformin is medication nonadherence that still has to reach a nurse; the request for secrecy cannot be honored. |
| 14 | How do I use the new cuff? It says ERR | non_clinical | admin | Device error code; admin or the equipment vendor handles cuff support, not a clinical question. |
| 15 | STOP | non_clinical | admin | Opt-out keyword arriving after a slow reply; admin processes the opt-out and should flag the delay as the likely cause. |

## What the dashboard shows after you deploy

Open `http://127.0.0.1:8765/dashboard`. It refreshes every ten seconds, so the deployment appears without a reload.

Four things move.

**The Exhibit B table** gains a working "Next quarter" column. Before the deploy it is the same story getting worse: median nurse response climbing from 31 hours to 84, overtime from 1,150 hours a month to 1,810, three more nurses gone, another 489 patients going quiet. After the deploy, the same column is computed with your triage agent in it.

**The "Urgent cases missed / week" tile** turns from a zero into a number if your thresholds downgraded anything. This is where message 12 shows up, several days later, as a count of people.

**The trend charts** — escalations, nurse response, overtime, patients inactive after an escalation — get a marker at week 40, where your deployment goes live, and the lines bend or they do not.

**The Sign Prairie toggle** draws weeks 40 to 52 with and without your deployment. Until you deploy something, those two lines sit exactly on top of each other, because there is nothing to compare. That is the honest before-picture: signing Prairie takes patients from 40,000 to 100,000, and the model puts median nurse response at 336 hours — the cap, two weeks — either way.

## How your four decisions reach the numbers

The acceptance run does not just print a table. It writes three numbers, and those three numbers are the only thing the company model is told about your agent.

| From the acceptance run | Into the model | What it does there |
|---|---|---|
| Share of non-clinical messages routed away from nurses | `inbound_to_nurse_share` | How much of the inbound flood still lands on a nurse. Route all of it away and this falls from 0.60 to 0.0. |
| Fixed at 0.6 when triage is live | `routine_time_factor` | Routine escalations cost a nurse less time once they arrive pre-sorted, and urgent cases jump the queue: urgent response drops to 4 hours. |
| Urgent recall | `urgent_recall` | Anything below 1.0 becomes missed urgent cases every week, forever, on the tile. |

From there the model is short enough to read: items on the queue divided by nurse capacity gives a load, and load above 0.8 pushes the median response up an exponential curve to a cap of 336 hours. Fewer items means a lower load, a shorter wait, less overtime, fewer resignations, fewer patients going quiet.

That is the whole mechanism, and it is worth saying plainly to the room: your decisions changed a prompt, the prompt changed a score, the score changed three parameters, and the parameters changed the company. Nothing in that chain is hidden, and every step of it is a file you can open.
