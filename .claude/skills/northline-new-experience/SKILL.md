---
name: northline-new-experience
description: Scaffold a fresh copy of this course's skills and empty tool registry for your own company, next to this repo. Usage /northline-new-experience <name>
arguments: [name]
disable-model-invocation: true
---

Run `uv run python scripts/new_experience.py $name`. It creates `../$name` with the take-home skills renamed for your company (`/$name-setup`, `/$name-brief`, `/$name-tools`, `/$name-agent`, `/$name-pm-run`, `/$name-expand`, `/$name-deploy`), an empty tool registry, and no corpus — the loop runs on your own first conversations, not generated ones.

Then:

```
cd ../$name && uv sync && uv run python scripts/check.py
```

Report the path it printed and the check's last line. Tell them: open Claude Code in `../$name` and run `/northline-brief $name`.

No corpus on purpose. Never run git.
