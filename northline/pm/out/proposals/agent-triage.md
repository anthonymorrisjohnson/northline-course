# Deployment proposal: `triage`

**Kind:** agent  **Placement:** Inline between the check-in agent's escalation output and the nurse queue. Every escalation the check-in agent emits is handed to triage first; triage resolves, redirects, or passes through before anything touches the nurse queue. No escalation reaches a nurse without passing through this layer.

## Why
Reduce nurse queue volume and response latency by autonomously handling non-clinical escalations and correctly prioritizing what remains. The agent calls pending_messages to read the current escalation backlog, tier_message to assign a priority tier (urgent / routine / administrative), and route_message to either resolve the item in-place (scheduling edits, portal resets, billing questions), redirect it to the appropriate non-clinical queue, or pass it to the nurse queue with the tier already set. Target: remove the 40 % non-clinical load from nurses entirely and surface the 344 weekly items that exceed 24 h unanswered at the front of the queue rather than buried in arrival order.

Evidence from the queue log: 2401 escalations a week, median nurse response 29.6 hours (p90 72.9), 40% of the nurse queue is non-clinical, 344 escalations unanswered over 24 hours from 342 patients.

## Tools it needs
- `pending_messages — reads the escalation backlog; required to know what to act on`
- `tier_message — assigns urgent / routine / administrative priority based on symptom language, vital-sign keywords, and time-since-check-in; the safety-critical classification step`
- `route_message — executes the routing decision: resolve in-place, redirect to non-clinical staff, or forward to nurse queue with tier metadata attached`

## Decisions a human must make before it goes live
1. Urgent thresholds: the systolic and diastolic blood pressure, the low and high glucose, and the symptom words that are always urgent.
2. Non-clinical handling: route to admin staff, auto-reply from approved content, or hold for the morning.
3. After-hours rule: what happens to an urgent message at 1:48am when no nurse is on shift.
4. Consent: whether 'don't tell the doctor' is honoured, and what the patient is told either way.

## Acceptance test
Score the fifteen overnight texts from Exhibit E against the nurse-authored answer key. Each message receives a tier label (urgent / routine / administrative) and a route decision (nurse queue / non-clinical redirect / auto-resolve). Pass criteria: (1) zero urgent messages misclassified as routine or administrative — this is a hard gate, one failure is a rollback trigger; (2) tier agreement with the nurse key ≥ 13 of 15 (87 %); (3) route agreement ≥ 12 of 15 (80 %); (4) no message that the key marks nurse-queue ends up auto-resolved. Run the test on the committed corpus in northline/pm/out/classified.jsonl as ground truth for automated regression. Human nurse reviewer signs off on any disagreement before the agent goes live.

## Metrics it should move
- Nurse queue volume: from ~2401 escalations/week toward ≤1450 (remove the ~40 % non-clinical share)
- Median nurse response time: from 29.6 h toward ≤12 h as nurses work a smaller, better-prioritized queue
- Unanswered-over-24h count: from 344/week toward ≤50/week by surfacing aged items at queue head and auto-resolving administrative ones immediately
- Non-clinical items reaching nurses: from 40 % toward <5 % of queue volume
- Triage false-urgent rate (administrative tiered as urgent): track weekly; alert if >2 % to catch prompt drift

## Risks
**Downgrade of an urgent case (primary risk).** tier_message misreads a patient's message — vague pain language, atypical presentation, non-native phrasing — and assigns routine or administrative, delaying nurse contact for a deteriorating patient. Mitigations: (a) the acceptance test hard-gates on zero urgent misses before any production traffic; (b) any message containing vital-sign keywords (BP readings, O2 sat, glucose values, chest/breath/pain) is unconditionally escalated to urgent regardless of the model's tier score; (c) when tier_message confidence is below threshold the item routes to nurse queue as urgent-unscored rather than being classified; (d) weekly audit of a random 50-item sample by a charge nurse to catch systematic drift. **Scope creep into clinical advice.** route_message auto-resolving an item that looks administrative but contains an embedded clinical question. Mitigation: auto-resolve is restricted to a whitelist of message types (appointment reschedule, portal password, billing inquiry, prescription refill status where pharmacy has already confirmed); anything outside the whitelist routes to a human. **Queue opacity.** Nurses lose visibility into what triage handled. Mitigation: route_message writes a structured log entry for every action; nurses can query the resolved-by-triage bucket at any time and flag misroutes for retraining. **Latency addition.** Triage adds a processing hop. Mitigation: triage must complete classification and routing within 90 seconds of receipt; items exceeding this SLA are immediately forwarded to nurse queue as urgent-unscored so the hop never delays a nurse seeing an item.

## Decision
- [ ] Approve: `/deploy triage`
- [ ] Reject, reason:
