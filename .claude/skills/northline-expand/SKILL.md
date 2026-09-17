---
name: northline-expand
description: Implement one approved tool proposal end to end: spec, failing tests, function, registry line, tests green, and how to see it in both front doors. Usage /northline-expand tool-request_refill
arguments: [proposal]
---

Implement `northline/pm/out/proposals/$proposal.md`. Read it. Then follow the repo's one procedure for adding a tool; the point is that it is short.

1. **Spec.** Copy `templates/tool-spec.md` to `northline/tools/specs/$proposal.md`, filling every placeholder from the proposal. Module: `patient.py` when the tool serves patients through the check-in agent (the proposal's persona line says patient, or mentions the SMS agent or nurses acting for a patient); `plan.py` when it serves health-plan analysts. Keyword arguments, typed. `requires` is `none` unless the proposal says the tool belongs to an agent. Three test cases minimum: happy path, `not_found`, `error`.
2. **Tests first.** Add them to `tests/test_patient_tools.py` or `tests/test_plan_tools.py` in the existing style, using the `data_dir` and `log_dir` fixtures. Run `uv run pytest -q` and confirm they fail.
3. **Function.** Add it with the docstring from the spec. Never raise; return `status`. Use `store.load`, `store.save`, `store.append`. New data file: `northline/data/<name>.json` with three realistic seed rows.
4. **Register.** One `_t(...)` line in `northline/tools/registry.py`. Then add the new tool's name to the expected set for its persona in `tests/test_registry.py::test_persona_selection` (that test pins the exact tool list on purpose). Run `uv run pytest -q`; all green.
5. **Guardrail.** If the proposal would give a patient clinical advice or a result interpretation, the function returns `{"status": "error", "message": "..."}` explaining a nurse handles that, and you say so.
6. **Show it.** Three lines: restart the agent server and ask for the new capability on the check-in page; start a new Claude Code session so front door 1 picks up the tool; re-run `/northline-pm-run` later to watch the candidate shrink.

Never run git. Do not change existing signatures. Do not edit `brief.md` unless the proposal's safety notes require a new rule, and show the diff first.
