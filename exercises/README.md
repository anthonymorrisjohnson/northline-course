# Take-home exercises

These three exercises are for running the Northline loop on a business that is not Northline, either in your head or on your laptop.

Each one gives you a company, two personas, and the same three questions: which front door for each persona, which three tools ship first, and which number tells you the bottleneck has moved. They are deliberately different from each other. One lands on a customer's agent over MCP (Model Context Protocol, the standard way to hand an assistant a set of tools), one on an agent you host, one on both.

## Two tracks

**Read track — about twenty minutes, no laptop.** Read the company, answer the three questions on paper, then read the answer sketch. Good on a plane. Good for a leadership team to do together and compare.

**Build track — about an hour, laptop.** Scaffold a fresh copy of the course's skills for that company, interview yourself with `/northline-brief`, build the tools it names, install the agent brief, have five real conversations with it, then run `/northline-pm-run` on your own five conversations and see what the loop says about them. The point is not the tools. The point is watching a loop that has only ever seen five conversations still tell you something you did not plan.

The diagnosis and proposal prompts in `northline/pm/diagnose.py` and `propose.py` describe Northline; edit their first sentences for your company before running `/northline-pm-run` in a scaffold.

Do the read track first even if you intend to build. The build track will disagree with you, and that is more useful when you have written down what you thought.

## About the answer sketches

Every exercise ends with an answer sketch. It is **one defensible answer, not the answer.**

The front-door decision in particular has no correct value. It has a trade you are choosing to make, and the sketch names which one. If your answer differs from the sketch, the useful question is not who is right — it is which column of the front-door table you weighted more heavily, and whether you would defend that weighting to a board.

The bottleneck question is different. There, a wrong answer is usually recognisable: it names a queue that does not grow when the agent works. If your answer and the sketch disagree about the bottleneck, one of you has missed a queue.

## The three

| Exercise | Company | Where it lands |
|---|---|---|
| [01](01-pharmacy-chain.md) | A regional pharmacy chain | MCP for one persona, a controlled agent for the other |
| [02](02-health-insurer.md) | A mid-size health insurer | The reverse split, for reasons worth arguing about |
| [03](03-telemedicine-startup.md) | A telemedicine startup | Both doors on one tool layer, and a bottleneck you have seen before |

## Before the build track

You need the course folder you already have, and `uv`. `/northline-new-experience <name>` creates a sibling folder next to it with the take-home skills, an empty tool registry, and no corpus — the loop runs on conversations you have yourself, not generated ones.

Nothing in these exercises touches the Northline folder.
