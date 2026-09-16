---
name: tools
description: Read briefs/$name.md and build any tool it names that does not exist yet, running the /expand procedure for each. Usage /tools <name>
arguments: [name]
---

Read `briefs/$name.md`. From section 2 (the jobs, ranked) and section 7 (first release), list the tools it names. For each one that is not already a line in `northline/tools/registry.py`, run the repo's one procedure for adding a tool — the same one `/expand` uses:

1. **Spec.** Copy `templates/tool-spec.md` to `northline/tools/specs/<tool_name>.md`, filling every placeholder from the brief's description of that job. Module: `patient.py` when the tool serves the persona that talks to the check-in agent; `plan.py` when it serves the persona that works through MCP. Keyword arguments, typed. `requires` is `none` unless the brief says the tool belongs to a not-yet-deployed agent. Three test cases minimum: happy path, `not_found`, `error`.
2. **Tests first.** Add the tests to `tests/test_<module>_tools.py`; if that file does not exist, create it with `from northline.tools import <module> as m` and the `data_dir`/`log_dir` fixtures from `tests/conftest.py`. Run `uv run pytest -q` and confirm they fail.
3. **Function.** Add it with the docstring from the spec. Never raise; return `status`. Use `store.load`, `store.save`, `store.append`. New data file: `northline/data/<name>.json` with three realistic seed rows.
4. **Register.** Add one `_t(...)` line to `northline/tools/registry.py`. If `tests/test_registry.py` exists, add the tool's name to the expected set in `test_persona_selection` (that test pins the exact tool list on purpose). If it does not exist, create it with one test asserting `{t.name for t in registry.select('<persona>')}` contains the new tool. Run `uv run pytest -q`; all green before moving to the next tool.

Stop after five tools even if the brief names more; say which were skipped and why.

Never run git. Do not change existing signatures. Do not edit `brief.md` unless a tool's safety notes require a new rule, and show the diff first.
