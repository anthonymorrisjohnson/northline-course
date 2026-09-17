# Northline Care: slide outline

Fifteen slides for the two presenters. A white setup slide first, then a dark title slide, white content slides, one table or one image per slide. Speaker notes below each slide go into the deck's notes pane.

## Slide 1: Three things, then wait for us

- Shown on screen while people arrive, and left up until the last READY line. Three cards: open the Claude desktop app, New project, a new empty folder called `northline`; paste the line in the band below and, when it finishes, close and reopen the project; `/northline-setup`, stop at READY
- Band: the line to paste. "Download github.com/anthonymorrisjohnson/northline-course as a ZIP, unzip it so the files sit directly in this folder, then delete the zip."
- No terminal anywhere on this slide. The server window, texting the agent, `/northline-pm-run` and `/northline-deploy triage` are cued from the front at minute 25

Speaker: do not present this slide. Point at it. Walk the room while it is up and look for anyone stuck on step 1; that is the person who needs help before anything else. Expect 40 to 70 model calls per laptop on their own Claude account over the hour.

## Slide 2: Moving the bottleneck, live

- A 75-minute workshop: a paper case, a live tool loop, a board meeting you have to defend
- Two roles: Room reads the case and asks the questions; Screen drives the dashboard and two commands
- Two commands all session: `/northline-pm-run`, `/northline-deploy triage`

Speaker: what the room will do in 75 minutes. Land it before the email goes up: everything that follows is the same case, run live.

## Slide 3: The Monday email

- From: VP Network Partnerships, Prairie Health Plan
- To: CEO, Northline Care
- Subject: Contract for signature, 60,000 members
- "Good morning, Attached is the executed agreement from our side for chronic care management of 60,000 Medicare Advantage members across North Dakota, South Dakota, and Minnesota, at the rate we discussed. Go-live is 90 days from signature. We've been impressed by your engagement numbers. We do need your signature by Friday; after that we'll proceed with the other vendor in our process. Looking forward to working together."

Speaker: read this aloud, cold, and nothing else. Let the room sit with it before anyone says a word.

## Slide 4: Two front doors, one tool layer

- Diagram: Patients (left) → the check-in agent Northline built and hosts → Northline's tools
- Diagram: Prairie's analyst (right) → her own Claude Code, her own agent → the same Northline tools, over MCP
- One tool layer, `northline/tools/`, serving both doors; a tool added for one is available at the other the moment it is registered

Speaker: this is how Prairie got impressed. Her agent pulled the engagement numbers herself, on her own schedule — Northline built the tools, Prairie's analyst ran the loop.

## Slide 5: The loop

- `corpus/patient`, `corpus/plan`, `corpus/queue.jsonl` → **classify** (calls Claude) → `classified.jsonl`
- → **aggregate** (plain Python) → `report.md`, `queue_metrics.json`
- → **diagnose** (calls Claude) → `diagnosis.md`, naming the bottleneck and the one metric to watch
- → **propose** → tool-expansion proposals and the triage deployment proposal → `/northline-expand` or `/northline-deploy`

Speaker: the whole run takes about five minutes; roughly half of it is the classification step. Talk through the wait — that pause is where half the teaching happens.

## Slide 6: Four decisions, filled live

- **Thresholds:** _[blank — filled live]_
- **Non-clinical handling:** _[blank — filled live]_
- **After-hours rule:** _[blank — filled live]_
- **Consent ("don't tell the doctor"):** _[blank — filled live]_

Speaker: four decisions, one at a time, voted by the room during `/northline-deploy triage`. Each has a Northline default; say so, and don't let the room take all four without a vote.

## Slide 7: Pushback questions

- "You'll fix operations in parallel. What specifically will be different on day 91, and how do you know?"
- "You raised the escalation threshold. Which patients are now not getting a call, and would you tell them?"
- "If we decline, Prairie goes to a competitor. What's our growth story for the next raise?"
- "Your triage assistant looks great. What did it do with the 184/112 reading?"
- "Who is paying for the extra care the agent uncovered?"

Speaker: one per click, during the board meeting. Toggle "Sign Prairie" on the presenting team's own numbers while they answer. Read them one at a time; do not show all five at once.

## Slide 8: You didn't automate the bottleneck, you moved it

- Table: Exhibit B, "Before" and "Last quarter" columns from the dashboard
- Nurses: 25 → 22. Nurse response, median: 4.0h → 31.1h. Overtime: 180h/month → 1,151h/month. Resignations: 0 → 3. Inactive after escalation: 0 → 340
- After-hours share: 0% → 46%. Escalations/week: 300 → 2,400

Speaker: readings went up tenfold and engagement hit 78%, and the same motion that produced those numbers produced this table. The agent didn't remove the bottleneck — it moved it from patients not being reached to nurses not being able to answer.

## Slide 9: Tuning parameters are strategy decisions in disguise

- Table: the Exhibit E acceptance run, systolic/diastolic raised to 190/115, message 12 marked
- Accuracy 93%. Urgent recall 0.75. Missed urgent: [12]. Non-clinical routed away from nurses: 100%
- Message 12 — "BP 184/112, bit of a headache, probably nothing" — expected `urgent_clinical`, got `non_urgent_clinical`: **MISS**

Speaker: 184 is below 190, and the prompt applies the number literally. Nobody wrote a bug — a room raised a threshold because it sounded cautious in a meeting, and a real patient's reading fell under it.

## Slide 10: AI lets you pivot fast

- Chart: nurse response median (hours), weeks 1–52, from the dashboard's trend data
- The line sits at 22.2h under the check-in agent, steps up to 28.3h, 36.7h and 48.9h as the three nurses resign in the last quarter, then drops to 4.0h the week triage deploys (week 40) and stays there
- Median nurse response: 31.1h → 4.0h. But urgent cases missed/week: 0.0 → 90.0
- Caption: "Numbers from a triage deployment made with the 190/115 decisions on this laptop; your room's numbers will differ. Show the live dashboard."

Speaker: every queue number gets better in a day. Read the last row before anyone celebrates the rest of the table. Numbers from a triage deployment made with the 190/115 decisions on this laptop; your room's numbers will differ. Show the live dashboard.

## Slide 11: A fast fix still needs testing

- Table: the nurse key's four traps, `northline/agents/triage/nurse_key.json`
- \#5 — "Sugar was 62 before bed. Had some juice" — sounds resolved; nocturnal hypoglycemia still needs a same-night follow-up
- \#9 — "Sore on my foot, two weeks, doesn't hurt" — painless and downplayed; a two-week non-healing diabetic foot sore is a classic silent complication
- \#12 — "BP 184/112, bit of a headache, probably nothing" — the patient's own "probably nothing" invites under-triage of a hypertensive urgency
- \#13 — "Stopped the metformin. Don't tell the doctor" — medication nonadherence still has to reach a nurse; the request for secrecy cannot be honored

Speaker: the key is marked `"draft": true` — illustrative, not a clinician's sign-off. Good enough to argue about in a workshop, not good enough to route a real patient.

## Slide 12: Business model matters

- Chart: the Sign Prairie toggle, weeks 40–52, nurse response median (h), with vs. without the deployment
- Without new deployments: flat at 336.0h — the model's cap, reached before week 40
- With new deployments: 31h at week 40, climbing to 57h by week 52 as three more nurses leave. Triage buys a quarter; it does not staff the contract
- Caption: "Numbers from a triage deployment made with the 190/115 decisions on this laptop; your room's numbers will differ. Show the live dashboard."

Speaker: same contract, same 100,000 patients, two very different lines — and the only thing that moved between them is a prompt four people voted on this afternoon. Then point at the slope of the lower line: it is still climbing, because nurses are still leaving. The prompt bought time, not headcount. Numbers from a triage deployment made with the 190/115 decisions on this laptop; your room's numbers will differ. Show the live dashboard.

## Slide 13: Where each front door belongs

- Table: the two front doors, from `docs/01-front-doors.md` — MCP given to the customer vs. a controlled agent you host
- Rows: who runs the loop, distribution, what you see, guardrails, who pays for tokens, liability, build cost, time to first user, what Prairie saw
- **Highlighted row — what Prairie saw:** "78% engagement, tenfold readings" vs. "Nothing; they never asked for escalations"

Speaker: the highlighted row is the whole lesson. The customer saw the outcomes. Nobody showed them the queue, because nobody built a tool that answers that question.

## Slide 14: Case one in one slide

- "Build-versus-buy is a go-to-market question. What is good enough to sell in one country may not be good enough in another: regulation, clinical standards, liability, and buyer expectations all differ."

Speaker: hold this one line. It is the reason the four decisions on slide 6 have no universal right answer — only a market that is or isn't willing to accept them.

## Slide 15: Take it home

- Unzip the course folder, run `/northline-setup`
- Type `/northline-new-experience` and build a third front door for a persona this repo doesn't cover
- Three take-home exercises, in the exercises folder, each buildable with the same skills used today
- The question to carry out of the room: **where is this bottleneck hiding in your market?**

Speaker: everything you watched happen today is a committed file in your own folder. Nothing here needs the network except the two model calls — go rerun them on your own numbers.
