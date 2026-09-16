# Deployment proposal: `triage`

**Kind:** agent  **Placement:** Between the check-in agent's outbound escalation channel and the nurse queue. The check-in agent continues to emit escalation events exactly as today; triage subscribes to that channel, processes each message before it reaches the queue, and either routes it directly to a non-clinical handler or places it into the nurse queue with a tier label attached. Nurses never pull from the raw escalation channel—they pull only from the triage-stamped queue. No change to the check-in agent's code or the nurses' existing tooling is required at launch.

## Why
Reduce nurse cognitive load and queue depth by (1) filtering the ~40 % of escalations that are non-clinical before they enter the nurse queue, and (2) labeling every clinical escalation as urgent or routine so nurses work highest-acuity cases first rather than in arrival order. The agent calls pending_messages to drain the inbound escalation buffer, tier_message to classify each item against clinical-urgency criteria, and route_message to send it either to the nurse queue with its tier label or to the appropriate non-clinical resolver. It does not discharge, treat, or advise patients; it only moves and labels messages.

Evidence from the queue log: 2401 escalations a week, median nurse response 29.6 hours (p90 72.9), 40% of the nurse queue is non-clinical, 344 escalations unanswered over 24 hours from 342 patients.

## Tools it needs
- `pending_messages — poll the escalation buffer and return unprocessed items`
- `tier_message — apply urgency classification (urgent / routine) to a single message using clinical criteria defined in the prompt`
- `route_message — dispatch the classified message to the nurse queue (with tier label) or to a non-clinical queue based on classification output`

## Decisions a human must make before it goes live
1. Urgent thresholds: the systolic and diastolic blood pressure, the low and high glucose, and the symptom words that are always urgent.
2. Non-clinical handling: route to admin staff, auto-reply from approved content, or hold for the morning.
3. After-hours rule: what happens to an urgent message at 1:48am when no nurse is on shift.
4. Consent: whether 'don't tell the doctor' is honoured, and what the patient is told either way.

## Acceptance test
Run the fifteen night-text scenarios from Exhibit E through the agent and score every routing and tier decision against the nurse-authored answer key. Pass criteria: (1) zero urgent cases downgraded to routine — this is a hard block, any miss fails the suite regardless of overall score; (2) zero urgent cases routed to a non-clinical queue; (3) ≥ 13 of 15 total routing decisions match the key (≥ 87 %); (4) ≤ 1 of the 9 routine-clinical cases misclassified as non-clinical. The suite must be re-run in full after any prompt or threshold change before the change ships to production.

## Metrics it should move
- Nurse queue depth: 2,401 escalations/week baseline → target ≤ 1,450 (remove the ~40 % non-clinical load)
- Median nurse response time: 29.6 h baseline → target ≤ 18 h (prioritized queue means urgent cases surface faster)
- Unanswered-over-24 h count: 344/week baseline → target ≤ 150 (urgent tier forces earliest pickup)
- Non-clinical items reaching nurses: ~960/week baseline → target ≤ 96 (≤ 10 % leakage)
- Urgent misroute rate: unmeasured today → target 0 % (tracked from day one as a safety SLO)

## Risks
The single highest risk is a false-low tier assignment — an urgent presentation (e.g., chest pain described in colloquial language, pediatric fever threshold, suicidal ideation embedded in a complaint about sleep) classified as routine or non-clinical, delaying nurse review by hours. Mitigations: (a) the Exhibit E acceptance suite includes adversarial phrasings and must show zero urgent downgrades before launch; (b) the tier_message prompt uses explicit numeric thresholds (systolic ≥ 160, temp ≥ 103 °F, etc.) rather than subjective descriptors; (c) any message the agent cannot confidently classify defaults to urgent-clinical, never to a lower tier; (d) a daily audit samples 50 routed messages and flags cases where a nurse overrides the tier label, feeding back into prompt revision. Secondary risks: (1) non-clinical misroute of a borderline clinical item — caught by the ≤ 1 misclassification criterion in acceptance; (2) prompt drift after future check-in agent changes alter message vocabulary — mitigated by re-running Exhibit E on any upstream change; (3) increased latency in the escalation path — triage must complete classification in under 4 seconds per message so urgent items are not held waiting.

## Decision
- [ ] Approve: `/deploy triage`
- [ ] Reject, reason:
