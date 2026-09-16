# Deployment proposal: `triage`

**Kind:** agent  **Placement:** Triage sits inline between the check-in agent's escalation output and the nurse queue. When the check-in agent calls its escalate action, the message is delivered to triage rather than directly to the queue. Triage then either routes the message into the nurse queue (flagged with a tier) or deflects it to a non-clinical channel. The nurse queue never sees a message that triage has not processed; triage is the sole entry point.

## Why
Triage reduces nurse cognitive load and queue depth by doing three things before any message reaches a nurse. First, it reads the backlog with pending_messages so it has context on what is already waiting — preventing duplicate escalations from inflating the queue. Second, it scores each incoming message with tier_message, assigning Tier 1 (clinical, time-sensitive), Tier 2 (clinical, routine), or Tier 3 (non-clinical / administrative) using the symptom descriptors, vital-sign flags, and time-of-submission signals in the message. Third, it calls route_message to send Tier 1 and Tier 2 items to the nurse queue with their tier label and to redirect Tier 3 items to the administrative channel, a self-service flow, or a templated auto-reply. The goal is to shrink the 39 % non-clinical fraction to near zero in the nurse queue, shorten median response time by removing noise, and eliminate the 238 messages per week that sit unanswered beyond 24 h by surfacing Tier 1 items with an urgency flag that triggers an on-call notification if no nurse has touched the message within two hours.

Evidence from the queue log: 155 escalations a week, median nurse response 28.9 hours (p90 69.7), 39% of the nurse queue is non-clinical, 238 escalations unanswered over 24 hours from 219 patients.

## Tools it needs
- `pending_messages — fetch the current nurse queue backlog so triage can detect duplicates and assess queue pressure before routing`
- `tier_message — classify a single escalation as Tier 1, Tier 2, or Tier 3 using clinical keywords, vital-sign thresholds, symptom severity signals, and submission timestamp`
- `route_message — send the tiered message to the correct destination: nurse queue for Tier 1 and Tier 2, administrative or self-service channel for Tier 3; attaches tier label, original timestamp, and check-in agent session ID`

## Decisions a human must make before it goes live
1. Urgent thresholds: the systolic and diastolic blood pressure, the low and high glucose, and the symptom words that are always urgent.
2. Non-clinical handling: route to admin staff, auto-reply from approved content, or hold for the morning.
3. After-hours rule: what happens to an urgent message at 1:48am when no nurse is on shift.
4. Consent: whether 'don't tell the doctor' is honoured, and what the patient is told either way.

## Acceptance test
Score the fifteen night texts in Exhibit E against the nurse-authored answer key. Each message receives a tier (1, 2, or 3) from triage and a disposition (queue vs. deflect). The nurse key provides the ground-truth tier and disposition for each of the fifteen messages.

Pass criteria:
- Tier 1 precision ≥ 95 %: of the messages triage calls Tier 1, at least 95 % must be Tier 1 in the nurse key. This bounds the false-alarm rate on urgent notifications.
- Tier 1 recall = 100 %: every message the nurse key marks Tier 1 must be called Tier 1 by triage. Zero misses on urgent cases is a hard gate; the agent does not deploy if any Tier 1 is downgraded to Tier 2 or Tier 3.
- Tier 3 precision ≥ 90 %: of the messages triage deflects, at least 90 % must be Tier 3 in the nurse key. This prevents clinical messages from being routed away from nurses.
- Overall agreement ≥ 87 % (13 of 15 messages must match the nurse key tier exactly).

The fifteen night texts were chosen because night-shift messages carry the highest misclassification risk — low staffing, brief patient language, and no daytime context cues. Passing on this slice is a necessary but not sufficient condition for deployment; a second evaluation on 30 additional held-out messages from the prior four weeks must also hit the same thresholds before go-live.

## Metrics it should move
- Nurse queue depth: 155 escalations/week → target ≤ 95 within 30 days (Tier 3 deflection removes the 39 % non-clinical share)
- Median nurse response time: 28.9 h → target ≤ 16 h within 30 days (smaller, higher-signal queue means nurses reach each item faster)
- Messages unanswered > 24 h: 238/week → target ≤ 50 within 30 days (Tier 1 two-hour on-call trigger catches items that would otherwise age)
- Tier 3 deflection rate: baseline 0 % (no deflection today) → target 35–42 % of all incoming escalations routed to non-nurse channel
- Tier 1 on-call trigger firing within 2 h: new metric, target ≥ 98 % of Tier 1 messages trigger notification before the 2 h window closes
- False deflection rate (clinical message sent to non-clinical channel): new metric, target < 1 % of all routed messages

## Risks
**Primary risk — downgrading an urgent case (Tier 1 → Tier 2 or Tier 3).** This is the only risk with patient-safety consequence. A chest-pain or respiratory-distress message that triage scores as Tier 2 delays the on-call notification by hours; scored as Tier 3, it never enters the nurse queue at all. Mitigations: (1) the acceptance test enforces 100 % Tier 1 recall as a hard gate — any miss blocks deployment; (2) tier_message is tuned with a conservative threshold that resolves ambiguous cases upward (toward Tier 1), accepting lower precision to protect recall; (3) for 30 days post-launch, a nurse spot-checks a random 10 % sample of Tier 2 and all Tier 3 deflections daily; (4) any message containing a predefined clinical keyword set (e.g., "chest," "breathing," "unresponsive," "bleeding," "fall") is hard-coded to Tier 1 before tier_message runs, bypassing the model classification entirely.

**Secondary risk — over-deflection of Tier 2 items.** If the Tier 2 / Tier 3 boundary is miscalibrated, routine clinical questions (medication refill, wound check) get sent to an administrative channel. These are not immediately dangerous but erode patient trust and create rework when patients re-escalate. Mitigation: the 30-day spot-check and a weekly precision report on Tier 3 dispositions, with a retraining trigger if false-deflection rate exceeds 2 %.

**Tertiary risk — queue pressure masking.** If pending_messages returns a stale snapshot (e.g., a caching lag), triage may route a duplicate Tier 1 as a new item and double-count urgency, or miss that a nurse already responded. Mitigation: pending_messages must return data no older than 60 seconds; the integration test suite asserts this SLA before deployment.

**Operational risk — triage becoming a single point of failure.** If triage is unavailable, escalations have no path to nurses. Mitigation: the check-in agent falls back to direct-to-queue routing if triage returns an error or times out after 10 seconds, preserving the pre-triage baseline as the failure mode.

## Decision
- [ ] Approve: `/deploy triage`
- [ ] Reject, reason:
