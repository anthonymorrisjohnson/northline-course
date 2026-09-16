---
name: generate-corpus
description: Author-only. Regenerate the committed corpus (patient transcripts, plan tool-call sessions, and the escalation queue) from the simulator's last-quarter numbers, with Exhibit E reseeded. Attendees never run this.
disable-model-invocation: true
---

You are regenerating the corpus, not running the workshop. This is an authoring step: it calls headless Claude about 160 times and takes several minutes, and it overwrites files under `corpus/`.

1. Confirm `northline/sim/out/summary.json` exists and has a `last_quarter` block; `generate_corpus.main()` reads its `nurse_response_median_h` for the queue's lognormal draw. If it is missing, run the simulator first.
2. Run `uv run pytest tests/test_generate_corpus.py -q`. All must pass before you generate anything: `plan()` determinism and theme mix, `queue_rows()` shape and after-hours share, the Exhibit E / nurse key files, and the `_valid_transcript` / `_valid_plan` validators.
3. **Ask the user to type "yes" before running generation.** This deletes and rewrites every file under `corpus/patient/` and `corpus/plan/`, costs about 160 to 300+ headless Claude calls at `model="sonnet"`, and takes several minutes to tens of minutes depending on how many items need re-asking. Do not run step 4 without an explicit "yes".
4. Run `uv run python -m northline.pm.generate_corpus`. It prints, per batch, how many items were written, how many were re-asked, and how many were dropped (still invalid after two extra attempts) — read that line; a nonzero drop count is expected occasionally, a large one is not. It also prints a final count of transcripts, plan sessions, and queue rows. If it raises `RuntimeError` after `claude_json`'s own retries (a headless call failed twice), just re-run it — files are overwritten by index, so a re-run is safe and does not duplicate anything.
5. Spot-check: read four or five files under `corpus/patient/`. Every one should have 4 to 8 messages, roles alternating starting with `assistant`, and no message that reads like the prompt itself. Refills, insurance, and loneliness should show up somewhere in the batch, and the escalated share across all transcripts should be roughly a third to two-thirds, not near-zero or near-all. Skim a few `corpus/plan/*.jsonl` files too — every `tool` value must be one of `member_engagement`, `outcome_evidence`, `enrollment_status`, `enroll_members`.
6. Check the aggregate numbers: `uv run python -c "from northline.pm.aggregate import *; print(queue_metrics(load_queue(REPO_ROOT/'corpus', REPO_ROOT/'northline'/'logs')))"`. Expect `nurse_response_median_h` near 31, `after_hours_share` near 0.46, `non_clinical_share_of_queue` near 0.40. If any of these are far off, look at `generate_corpus.THEMES` weights or `_stamp` before re-running — do not hand-edit the generated files.
7. Commit the result: `git add -A && git commit -m "Regenerate the corpus"`. This is the one skill in this project where committing is expected; every attendee-facing skill leaves git alone.

Never edit files under `corpus/` by hand. Never change `northline/agents/triage/exhibit_e.json` or `nurse_key.json` here — those are the case's fixed text and answer key, not generated content; `seed_exhibit_e()` only reads them.
