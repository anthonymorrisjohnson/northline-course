# Exercise 2: a mid-size health insurer

This exercise is for practising the front-door decision when the persona with the most volume is the one you can least afford to let someone else's agent speak for.

## The business

An insurer with 900,000 members, almost all through employer-sponsored plans, in eleven states. Member services handles about 40,000 calls a month and three questions are most of them: is this covered, where is my claim, and find me a doctor in network. Average handle time is eleven minutes and the team is 240 people, half of them contracted. Separately, 3,100 employer HR and benefits managers email their account manager for census counts, utilisation summaries and renewal modelling; each of those requests takes an analyst between an hour and three days, and the analysts are the reason renewal season is a crisis every year. The board has approved an AI budget on the strength of the call-centre number.

## Two personas

**Members.** They call because something already went wrong: a bill they did not expect, a claim that has not moved, a specialist who turned out to be out of network. They are not technical, they are often anxious, and what they are told about coverage they will reasonably treat as a promise.

**Employer HR and benefits managers.** They are analysts with spreadsheets and a renewal date. They want counts, trends and utilisation cuts, they want them in their own tools, and several of them already run an AI assistant over their own HR data.

## Where will the bottleneck move?

Write one sentence before you read on: **when members can get a straight answer about coverage at 9pm, whose queue grows?**

## Read track

1. **Front doors.** For each persona, which door — the tools handed to their own agent, or an agent you build and host? Name what you give up in each case.
2. **First three tools.** Which three ship first, and which persona is each one for?
3. **The bottleneck metric.** What is the one number that shows the bottleneck has moved, and who reads it every week?

## Build track

```
/new-experience insurer
cd ../insurer && uv sync && uv run python scripts/check.py
```

Then, in a Claude Code session in the new folder:

1. `/brief insurer` — answer as the insurer. When it asks where the bottleneck moves, do not answer "the call centre"; that queue is shrinking.
2. `/tools insurer` — it builds the tools your brief named, tests first, one at a time.
3. `/agent insurer` — it writes the agent brief and offers to install it as the live prompt. Say yes.
4. Start the page: `uv run python -m insurer.agent.server`, then open `http://127.0.0.1:8765`.
5. Have five conversations as a member. Make one of them a denied claim. Make one of them ask for something that would commit the insurer to paying, and read what the agent does with it.
6. `/pm-run` on your own five conversations.

## Answer sketch

*One defensible answer, not the answer.*

**The bottleneck moves to clinical review and appeals.** An agent that explains coverage clearly does not reduce the number of denials, it increases the number of members who understand they were denied and can act on it. Appeals go up, prior-authorisation requests go up, and both land on a small team of nurses and medical directors who are not on anyone's AI slide.

**Members get a controlled agent.** This is the reverse of the pharmacy's app customers, and the reason is liability. A sentence about whether something is covered is close to a promise to pay, and you cannot let that sentence be composed by an agent you do not own, wrapped in framing you never see. You also need the words: the reason a member is calling is a product defect, and it does not survive being reduced to a tool call.

**Employer HR gets MCP.** They already work in their own tools, they want data rather than conversation, and tool calls tell you everything that matters — which cuts they ask for, which arguments fail, which report they rebuild by hand every quarter because you never shipped it. Giving them the tools also takes the analyst out of the loop, which is the whole point.

**First three tools:** `coverage_check`, `claim_status`, `find_in_network_provider` — the three questions that are most of 40,000 calls a month. `coverage_check` is the one that needs a guardrail written before it ships: it states benefits, it never promises payment, and it says so in the reply.

**The metric:** median days from appeal received to decision, with a count of appeals past the regulatory clock beside it. The clinical operations lead reads it weekly, and it goes in front of the board next to the call-centre savings, on the same slide. Separately, watch the analyst hours HR requests consume — if that number does not fall after MCP ships, the tools are the wrong ones.
