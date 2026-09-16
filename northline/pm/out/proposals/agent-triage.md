# Deployment proposal: `triage`

**Kind:** agent  **Placement:** Inline, between the check-in agent's escalation output and the nurse queue. The check-in agent emits an escalation event; triage intercepts it before any nurse is notified. It calls pending_messages to read the full escalation context, calls tier_message to assign an urgency tier (urgent / clinical-routine / non-clinical), then calls route_message to send the item either forward to the nurse queue with the tier label attached, or sideways to the appropriate non-clinical path (scheduling, billing, admin). Nurses never see a message triage has not processed; triage never discards a message — it only re-addresses it.

## Why
Northline's nurse queue is the rate-limiting resource. At 2401 escalations per week with a 29.6 h median response and 344 items unanswered past 24 h, the bottleneck is not nurse capacity — it is queue composition. Forty percent of items (~960/week) are non-clinical and occupy the same attention as a post-surgical symptom. Triage exists to enforce a separation that nurses currently do manually and invisibly. It does three things: (1) removes non-clinical items from the nurse queue before they consume triage time, (2) attaches a tier label to every clinical item so urgent cases surface to the top of the queue automatically, and (3) produces a structured audit trail for each routing decision so the clinical team can review and correct the agent's judgement. The agent does not close cases, does not reply to patients, and does not override a nurse's decision once an item is in the queue.

Evidence from the queue log: 2401 escalations a week, median nurse response 29.6 hours (p90 72.9), 40% of the nurse queue is non-clinical, 344 escalations unanswered over 24 hours from 342 patients.

## Tools it needs
- `pending_messages — reads the full text, metadata, and prior conversation thread of each escalation so triage has enough context to tier accurately; must return the original check-in agent's confidence score and any sentinel flags it set`
- `tier_message — classifies the message as urgent, clinical-routine, or non-clinical; must emit a structured rationale field that the audit log captures; the tier is an input to route_message and is also stored on the escalation record permanently`
- `route_message — sends the tiered item to its destination: urgent and clinical-routine go to the nurse queue with the tier label prepended to the subject line; non-clinical items are dispatched to the configured non-clinical handler (scheduling desk, billing, or a patient self-service reply template) and removed from the nurse queue; every call to route_message writes a routing receipt that includes agent version, tier, destination, and timestamp`

## Decisions a human must make before it goes live
1. Urgent thresholds: the systolic and diastolic blood pressure, the low and high glucose, and the symptom words that are always urgent.
2. Non-clinical handling: route to admin staff, auto-reply from approved content, or hold for the morning.
3. After-hours rule: what happens to an urgent message at 1:48am when no nurse is on shift.
4. Consent: whether 'don't tell the doctor' is honoured, and what the patient is told either way.

## Acceptance test
The fifteen night texts in Exhibit E are the acceptance corpus. Each message was composed to represent a realistic 2 AM patient contact: a mix of urgent clinical symptoms, routine clinical follow-ups, and non-clinical requests (appointment changes, prescription refill logistics, billing questions). A senior nurse reviewed every message cold and recorded: (a) tier assignment, (b) intended destination, and (c) free-text rationale. That record is the nurse key.

Pass criteria (all three must hold simultaneously):

1. Zero urgent misses. Any message the nurse keyed as urgent must be tiered urgent by the agent. A single urgent item tiered clinical-routine or non-clinical is an automatic fail regardless of overall score. This criterion is not negotiable and cannot be offset by perfect scores elsewhere.

2. Overall tier accuracy ≥ 13/15 (87%). Ties between clinical-routine and non-clinical are scored as half-credit because the routing consequence is different but neither outcome reaches a nurse late.

3. Zero wrong-direction routes. An item the nurse keyed for the nurse queue must not be dispatched to a non-clinical path. An item the nurse keyed as non-clinical may be sent to the nurse queue (conservative error, not a fail) but counts against criterion 2.

The test is run against a shadow deployment before any live traffic is switched. The corpus and nurse key are version-controlled in the repo under tests/exhibit_e/. Any change to the agent's system prompt or tier_message schema requires re-running the full acceptance test before the change is promoted to production.

## Metrics it should move
- Nurse queue weekly volume: baseline 2401; target ≤ 1450 within 30 days (remove the non-clinical 40% plus reclassification of borderline items)
- Median first-nurse-response time: baseline 29.6 h; target ≤ 10 h at 60 days (queue compression plus urgent items surfacing to top)
- Unanswered escalations > 24 h: baseline 344/week; target ≤ 50/week at 60 days (urgent tier items should be answered same shift)
- Non-clinical items reaching nurse queue: baseline ~960/week; target ≤ 50/week (residual is conservative pass-throughs where triage was uncertain)
- Triage audit-trail coverage: 100% of escalations must have a routing receipt from day 1; this is a safety metric, not a quality metric

## Risks
The dominant risk is a clinical downgrade: a patient sends a message describing a time-sensitive symptom, triage tiers it non-clinical or clinical-routine, it leaves or languishes in the nurse queue, and the delay causes harm. This is the only risk that cannot be recovered from with a configuration change.

Mitigations in order of priority:

1. Sentinel-term hard override. Before tier_message is called, pending_messages scans for a fixed list of clinical alarm terms (chest pain, can't breathe, stroke, unresponsive, bleeding, overdose, suicidal, and equivalents). Any match forces an urgent tier regardless of the model's output. The sentinel list is maintained by the clinical lead, not the engineering team, and changes to it require sign-off.

2. Urgent tier is a pass-through. Route_message never routes an urgent-tiered item anywhere other than the nurse queue. There is no code path by which an urgent item reaches a non-clinical destination.

3. Confidence floor for non-clinical routing. Route_message only dispatches to a non-clinical path when tier_message returns non-clinical with a confidence score above a configurable threshold (initial setting: 0.92). Items below threshold fall through to the nurse queue as clinical-routine. This means the agent's errors are conservative — it adds noise to the nurse queue rather than removing urgent items from it.

4. Rollback is immediate. The routing layer is a feature flag. If the urgent-miss rate in production exceeds zero over any rolling 7-day window, the flag is flipped and all escalations revert to the nurse queue unfiltered within one deployment cycle. No data is lost; routing receipts are retained for post-incident review.

Secondary risks:

- Non-clinical items incorrectly held in nurse queue: the conservative threshold means ~5–10% of genuinely non-clinical items may still reach nurses in the early weeks. This is the intended failure mode and does not require intervention unless it persists past the 60-day calibration window.

- Routing receipt gaps: if tier_message or route_message fails silently, an escalation could stall in an indeterminate state. Mitigation: a watchdog job on pending_messages flags any escalation with no routing receipt after 15 minutes and sends it directly to the nurse queue with a "triage-error" label.

- Nurse trust erosion: if nurses see the agent mislabel items, they may start pulling items from the non-clinical path to recheck them, recreating the original workload. Mitigation: the weekly accuracy report is shared with the nursing team in their existing standup; nurses have a one-click "override and escalate" button on any routed item that also feeds a correction back into the retraining queue.

## Decision
- [ ] Approve: `/deploy triage`
- [ ] Reject, reason:
