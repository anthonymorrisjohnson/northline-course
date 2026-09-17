# Exercise 1: a regional pharmacy chain

This exercise is for practising the front-door decision when the two personas are as different as a phone in someone's pocket and a person standing behind a counter.

## The business

A chain of 180 pharmacies across four states, mostly in towns of under 20,000 people. It fills about 1.9 million prescriptions a year: maintenance medications, transfers from other chains, and weekly adherence packs for older customers. Two thirds of the calls that reach a store are the same two questions — is my prescription ready, and did my insurance go through. Those calls are answered by counter technicians, who take them standing at the till, in front of a queue of people who drove in. The chain has an app; about 11% of customers have it installed and roughly half of those have opened it in the last year. The CEO has been told to "do something with AI" and her instinct is a chatbot in the app.

## Two personas

**App customers.** They want status, refills, transfers and a price before they drive. A growing number of them already have an AI assistant on their phone and would rather ask it than open another app. They do not want a relationship with your software.

**Counter technicians.** They are the store's front line: phone, register, drive-through window, and the pharmacist's queue. They need to answer an insurance rejection, start a transfer, or tell someone why their pack is late, in a regulated conversation, while three people wait.

## Where will the bottleneck move?

Write one sentence before you read on: **when customers stop phoning to ask whether their prescription is ready, whose queue grows?**

## Read track

1. **Front doors.** For each persona, which door — the tools handed to their own agent, or an agent you build and host? Name what you give up in each case.
2. **First three tools.** Which three ship first, and which persona is each one for?
3. **The bottleneck metric.** What is the one number that shows the bottleneck has moved, and who reads it every week?

## Build track

```
/northline-new-experience pharmacy
cd ../pharmacy && uv sync && uv run python scripts/check.py
```

Then, in a Claude Code session in the new folder:

1. `/northline-brief pharmacy` — answer as the chain. It will push on where the bottleneck moves; do not let yourself off.
2. `/northline-tools pharmacy` — it builds the tools your brief named, tests first, one at a time.
3. `/northline-agent pharmacy` — it writes the agent brief and offers to install it as the live prompt. Say yes.
4. Start the check-in page: `uv run python -m pharmacy.agent.server`, then open `http://127.0.0.1:8765`.
5. Have five conversations as a customer. Make one of them easy. Make one of them something you did not build a tool for, and read what the agent says when it cannot help.
6. `/northline-pm-run` on your own five conversations. There is no corpus here, so the report is entirely about what you just said to it.

## Answer sketch

*One defensible answer, not the answer.*

**The bottleneck moves to the pharmacist.** The calls that disappear are the easy ones. What is left, plus what the assistant surfaces — transfers, prior authorisations, rejected claims, "can I get a 90-day instead" — all needs a pharmacist's signature, and each one takes minutes rather than seconds. The counter gets quieter and the verification queue behind it gets longer.

**App customers get MCP (Model Context Protocol, the standard way to hand an assistant a set of tools).** They already live in an assistant, they do not want another app, and for refill status and transfers the tool calls tell you everything you need: which lookups fail, which arguments people pass, which stores get asked for things they cannot do. You give up their words, which for status questions costs you very little.

**Counter technicians get a controlled agent.** Two reasons and they are both about control. The conversation is regulated, and you need to own every sentence that goes near a medication. And the technicians' words are the best product signal in the company — they are describing the failure the moment it happens, which no tool call will ever do.

**First three tools:** `refill_status`, `request_refill`, `insurance_rejection_reason`. The first two are most of the phone volume and serve both doors. The third is the one that turns an angry counter conversation into a five-second answer, and it is the tool the app persona will start calling too.

**The metric:** median hours from refill request to pharmacist verification, with a count of requests older than 24 hours next to it. The pharmacy operations lead reads it weekly. Watch it from the day the first tool ships, not from the day someone complains — the whole point is that this queue grows quietly while the visible one shrinks.
