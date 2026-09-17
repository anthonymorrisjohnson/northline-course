# Operating it

This page is for the week after the workshop: who reads what, what has to be signed before an agent is live, what it costs, and the number that stops a rollout.

## Somebody owns the backlog

One named person reads `northline/pm/out/report.md` every week. Not a committee, not a rota. The report is short on purpose: the board's numbers next to the logs, the outcomes, what patients raise by tier, and the candidate list with counts and quotes.

They are looking for three things. A candidate whose count is climbing. A queue metric that moved. And the quotes, which are the only part of the report that will change anyone's mind in a meeting.

Re-run `/northline-pm-run` to refresh it. The loop picks up anything new in `northline/logs/` alongside the committed corpus, so the report grows with the product rather than being a snapshot of the day it was written.

## Every proposal ends in a decision box

Open any file in `northline/pm/out/proposals/` and scroll to the bottom:

```
## Decision
- [ ] Approve: `/northline-deploy triage`
- [ ] Reject, reason:
```

That box is there so that not building something is a recorded decision with a name and a reason on it, the same as building it. A backlog of unexplained silence is how a team ends up arguing about the same candidate for six months.

The reject reason matters more than the approval. "The queue metrics say this moves nothing" is a reason that saves the next reader a week.

## An agent is not live until it has been tested and signed

Two gates, both of them cheap, neither of them optional.

**The acceptance test runs first.** `/northline-deploy triage` renders the prompt, runs the fifteen Exhibit E messages against the nurse's key, and shows you the miss table before it shows you anything good. The deployment is registered afterwards. You always see what you got wrong before you see your improved numbers.

**A human signs the decisions.** `northline/agents/triage/decisions.json` holds the four choices and a `chosen_by` field. It says `northline_default` when every value is the default and `attendee` when any value was changed. In a real company that field carries a person's name, and that person is the one who answers for what the thresholds did. The file is small enough to read aloud in a meeting, which is the point.

Any change to a decision means re-running the acceptance test before the change ships. A prompt is not a config file you tweak on a Friday.

## What it costs

Be careful here, because this repo does not yet contain an honest price per conversation.

Every committed transcript carries a `cost_usd` field, and in all 120 of them it reads `0.0`. That is not a measurement. The corpus was written in bulk by `northline/pm/generate_corpus.py`, which sets the field to zero and moves on. The plan sessions record no cost at all — they are tool-call logs, and the tokens were spent in Prairie's own session, on Prairie's own bill.

The classification run does not record its cost either. `northline/pm/claude_json.py` asks for structured output and keeps the structured output; the run's cost is not written anywhere in `northline/pm/out/`.

So the number you can quote from this repo is zero, and zero is wrong. Here is where the real one comes from instead. A live conversation on the check-in page does record its cost: `northline/agent/transcripts.py` adds each turn's `cost_usd` to the transcript as it goes. Talk to the page, then read your own logs:

```
uv run python -c "import json,glob; c=[json.load(open(p))['cost_usd'] for p in glob.glob('northline/logs/transcripts/*.json')]; print(len(c), sum(c), sum(c)/len(c) if c else 0)"
```

That gives you conversations, total, and mean — measured, from your own laptop, on your own model choice. Before anyone puts a cost per patient per month in a board deck, run a few hundred real conversations and read that number. Do not estimate it from a price list, and do not quote the corpus.

## The metric that pauses a rollout

Two, and either one on its own is enough.

**Median nurse response above 8 hours.** Not the mean, which hides the tail, and not the 90th percentile, which panics the room. Eight hours is a working day: above it, a patient who wrote in the morning has not heard back by the evening. Northline's current median is 29.6 hours, so the number is not a hypothetical. It is the thing that is already wrong.

**Any missed urgent case.** Not a rate, not a threshold. One. The dashboard has a tile for it, it reads 0.0 when nothing is being downgraded, and it is the first thing to look at after a deployment. A triage layer that speeds everything up while quietly dropping one urgent message a week is worse than the queue it replaced, because the queue was at least slow in a way everyone could see.

Pausing means the deployment comes out and the previous behaviour comes back, not that someone adds it to a list.

## The business model does not pay for this

Northline charges $25 per patient per month. Forty thousand patients, a million dollars a month. That number has not moved since before the agent existed.

Everything else moved. Readings went from 12,000 a month to about 120,000. Escalations went from 300 a week to 2,400. Patients started sending 3,100 messages a week that nobody asked for and nothing tracked before. Nurse cost went from $233,100 a month to $265,740 with three fewer nurses on payroll, the difference all overtime — 180 hours a month before, 1,150 now.

Same fee. Eight times the work.

That is the part the technology cannot fix, and it gets worse with the contract, not better. The model puts Prairie at 100,000 patients: revenue $2.5m a month, nurse cost $669,290, almost all of it overtime, three more resignations in the quarter, and a median nurse response of 336 hours, which is the cap the model stops counting at. Signing the deal scales the revenue by two and a half and the nurse bill by nearly three.

A flat per-patient fee prices a service where the demand is fixed. An agent that works does not leave demand fixed — it surfaces demand that was always there and was never reaching you. If the price does not have a term for that, then every improvement in engagement is a cost increase you agreed to in advance.

The options are not technical: price the surfaced work, cap it, staff for it, or decide not to surface it. Pick one before signing, not after.
