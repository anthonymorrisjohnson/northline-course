# Deployment proposal: `triage`

**Kind:** agent  **Placement:** Sits in the escalation path immediately after the check-in agent emits an escalation event and before any message enters the nurse queue. The check-in agent calls `route_message` (or fires a queue event); the triage agent intercepts every such call, reads the backlog with `pending_messages`, scores each item with `tier_message`, and then calls `route_message` to place the item in one of three destinations: (1) urgent nurse queue — paged immediately, (2) standard nurse queue — normal FIFO order, or (3) self-service deflection — an automated reply sent back to the patient with no nurse touch required. The nurse queue only ever sees items that have already been scored and routed; the raw escalation bus is invisible to nurses.

## Why
Reduce nurse cognitive load and queue latency by doing three jobs the nurses currently do manually at inbox time. First, separate the 40 % non-clinical volume (refill reminders, appointment links, billing redirects) before it hits the nurse queue at all, deflecting those items to automated replies or the appropriate non-clinical channel. Second, sort the remaining clinical items by acuity so the 344 cases sitting unanswered beyond 24 h are not buried under routine follow-ups — urgent items surface to the top regardless of arrival order. Third, provide a structured reason-for-routing on every item so the nurse who opens a case already knows the triage rationale and does not have to re-read the original thread to decide priority.

Evidence from the queue log: 2401 escalations a week, median nurse response 29.6 hours (p90 72.9), 40% of the nurse queue is non-clinical, 344 escalations unanswered over 24 hours from 342 patients.

## Tools it needs
- `pending_messages — reads the full escalation backlog so triage can process items in acuity order rather than arrival order; also used to detect items approaching the 24 h unanswered threshold`
- `tier_message — scores a single message on a clinical acuity scale (e.g. 1 = deflect / non-clinical, 2 = standard nurse queue, 3 = urgent / page now) and returns a structured rationale that travels with the routed item`
- `route_message — dispatches the scored item to its destination channel (deflect, standard queue, urgent queue) and stamps the item with tier, rationale, and triage timestamp for audit`

## Decisions a human must make before it goes live
1. Urgent thresholds: the systolic and diastolic blood pressure, the low and high glucose, and the symptom words that are always urgent.
2. Non-clinical handling: route to admin staff, auto-reply from approved content, or hold for the morning.
3. After-hours rule: what happens to an urgent message at 1:48am when no nurse is on shift.
4. Consent: whether 'don't tell the doctor' is honoured, and what the patient is told either way.

## Acceptance test
Run the fifteen night-text fixtures from Exhibit E through the triage agent in a sandboxed replay harness. Score each output against the nurse-annotated key using three pass/fail criteria per item.

Criterion 1 — Tier match: the agent's tier assignment (deflect / standard / urgent) must match the nurse key exactly. A downgrade on any item the nurse marked urgent is an automatic overall failure regardless of aggregate score.

Criterion 2 — Rationale coherence: a second nurse (blinded to which items are agent-generated) rates each rationale as adequate or inadequate for clinical handoff. Adequate means the nurse could act without re-reading the original thread.

Criterion 3 — Route destination: the `route_message` call must target the correct channel for the assigned tier with no mismatches between tier and destination.

Pass threshold: 15/15 on Tier match with zero urgent downgrades; ≥13/15 on Rationale coherence; 15/15 on Route destination. Any failure halts deployment. A partial pass (e.g. rationale misses on non-urgent items only) may proceed to a monitored shadow deployment where triage routes are logged but nurses still work from the unmodified queue, with a re-score after 500 live items before go-live.

## Metrics it should move
- Median escalation response time: current 29.6 h, target ≤8 h at 90-day mark — primary outcome metric
- Unanswered-over-24h count: current 344/week, target ≤50/week — measures whether urgent surfacing is working
- Non-clinical items reaching nurse queue: current ~960/week (40% of 2401), target ≤100/week — measures deflection effectiveness
- Nurse time-to-first-action on urgent items: measured from triage timestamp to nurse first reply on tier-3 cases, target median ≤2 h
- Triage overturn rate: fraction of triage routing decisions manually changed by a nurse after opening the item, target ≤5% — leading indicator of model drift or calibration failure

## Risks
**Urgent downgrade (critical).** `tier_message` assigns tier 1 (deflect) or tier 2 (standard) to a message that a nurse would have scored tier 3 (urgent). The patient receives no timely clinical response. Mitigations: (a) the Exhibit E acceptance test fails hard on any urgent downgrade before go-live; (b) any item containing a keyword set (chest pain, can't breathe, bleeding, suicidal, severe, 911, emergency) bypasses `tier_message` entirely and is hard-routed to the urgent queue by rule before the model scores it — the model can only upgrade, never downgrade, items that match the keyword guard; (c) the nurse overturn rate metric is monitored daily in the first 30 days and an automatic circuit-breaker suspends triage routing if the rate exceeds 10% in any rolling 48-hour window, reverting to the unfiltered queue until human review clears the issue.

**Non-clinical misclassification (moderate).** A clinical item is deflected as non-clinical and receives an automated reply instead of reaching a nurse. Mitigation: deflection replies include a one-tap escalation link ("This doesn't answer my question") that re-queues the item directly to the standard nurse queue with a flag; the volume of re-queued deflections is tracked as a secondary safety metric.

**Rationale hallucination (moderate).** `tier_message` returns a plausible-sounding but clinically inaccurate rationale. The nurse trusts the rationale and skips re-reading the thread, missing context. Mitigation: rationales are presented as "triage note" with explicit framing that they are decision-support, not a clinical assessment, and the original message is always one click away in the same view.

**Backlog latency (low).** `pending_messages` returns a large backlog and triage processing time exceeds the real-time arrival rate during a surge, causing the agent to fall behind. Mitigation: triage processes in micro-batches with a maximum per-cycle cap; items older than 20 h are promoted to urgent automatically as a backstop regardless of tier score.

**Over-deflection gaming (low).** Patients learn that certain phrasings bypass triage to reach a nurse faster, causing non-clinical volume to re-enter the nurse queue through the escalation re-queue path. Mitigation: deflection re-queue rate is monitored; if it exceeds 15% of deflected volume, the deflection category thresholds are tightened in the next model calibration cycle.

## Decision
- [ ] Approve: `/deploy triage`
- [ ] Reject, reason:
