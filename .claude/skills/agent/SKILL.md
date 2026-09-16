---
name: agent
description: Write briefs/$name-agent-brief.md from templates/agent-brief.md, using the hard rules from briefs/$name.md, and offer to install it as the live agent prompt. Usage /agent <name>
arguments: [name]
---

Read `briefs/$name.md`. Fill `templates/agent-brief.md` and save it to `briefs/$name-agent-brief.md`:

- **Role**: one or two sentences from section 1 (who talks to it) and the top job from section 2.
- **Hard rules**: one bullet per guardrail kept from section 6, plus this one always, verbatim in spirit: "If asked for something no available tool does, say plainly you cannot do that yet, say what you can do, and offer to note it for a human. Do not invent a process."
- **Style**: inferred from the persona and channel in section 1.
- **Logging**: what is stored, that the product team reads it, and that gaps here are how the next tool gets built.

Keep the whole file under 60 lines.

Then offer to install it over `northline/agent/brief.md`. If they say yes, copy it in and run `uv run python -c "from northline.agent.prompt import system_prompt; print(system_prompt()[:300])"`. Show the user those first lines so they can see the new brief is live, and tell them to restart the agent server for it to take effect.

Never run git.
