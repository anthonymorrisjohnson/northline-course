---
name: brief
description: Interview the user about one AI experience from their own company and fill templates/use-case-brief.md, ending in a front-door decision and a guess at where the bottleneck will move. Usage /brief <short_name>
arguments: [name]
---

Fill `templates/use-case-brief.md` for "$name". One question at a time, two or three concrete options each, short answers accepted. Under ten questions; infer the rest and say what you inferred.

Order: personas and where they live (1); the top three jobs, then propose two more (2); the signal question (4); where the bottleneck will move (5), and push on it: "when this works, whose queue grows?"; guardrails (6), propose five and ask which to keep.

Write section 3 yourself with this rule of thumb, reasoning in the Why column:
- Users already live in their own AI assistant or a partner platform, and tool calls are enough signal -> MCP to their agent.
- Users come to you, the domain is regulated or high-stakes, you need their words as signal, or the channel is SMS or WhatsApp -> controlled agent.
- One persona each -> both, and name the shared tools.

Write section 7 last. Save to `briefs/$name.md`. Read back the front-door table and section 5 in three sentences and ask whether it matches their instinct. If it does not, ask what the table missed.
