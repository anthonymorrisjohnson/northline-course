---
name: generate-corpus
description: Author-only. Regenerate the committed corpus (patient transcripts, plan tool-call sessions, and the escalation queue) from the simulator's last-quarter numbers, with Exhibit E reseeded. Attendees never run this.
disable-model-invocation: true
---

You are regenerating the corpus, not running the workshop. This is an authoring step: it calls headless Claude about 160 times and takes several minutes, and it overwrites files under `corpus/`.

1. Confirm `northline/sim/out/summary.json` exists and has a `last_quarter` block; `generate_corpus.main()` reads its `nurse_response_median_h` for the queue's lognormal draw. If it is missing, run the simulator first.
2. Run `uv run pytest tests/test_generate_corpus.py -q`. All three must pass before you generate anything: `plan()` determinism and theme mix, `queue_rows()` shape and after-hours share, and the Exhibit E / nurse key files.
3. Run `uv run python -m northline.pm.generate_corpus`. It prints a count of transcripts, plan sessions, and queue rows when done. If it raises `RuntimeError` after retries (a headless call failed twice), just re-run it — files are overwritten by index, so a re-run is safe and does not duplicate anything.
4. Spot-check: read four or five files under `corpus/patient/`. Refills, insurance, and loneliness should show up somewhere in the batch, and at least a few conversations should have `"escalated": true`.
5. Check the aggregate numbers: `uv run python -c "from northline.pm.aggregate import *; print(queue_metrics(load_queue(REPO_ROOT/'corpus', REPO_ROOT/'northline'/'logs')))"`. Expect `nurse_response_median_h` near 31, `after_hours_share` near 0.46, `non_clinical_share_of_queue` near 0.40. If any of these are far off, look at `generate_corpus.THEMES` weights or `_stamp` before re-running — do not hand-edit the generated files.
6. Commit the result: `git add -A && git commit -m "Regenerate the corpus"`. This is the one skill in this project where committing is expected; every attendee-facing skill leaves git alone.

Never edit files under `corpus/` by hand. Never change `northline/agents/triage/exhibit_e.json` or `nurse_key.json` here — those are the case's fixed text and answer key, not generated content; `seed_exhibit_e()` only reads them.
