# Deployment proposal: `triage`

**Kind:** agent  **Placement:** Triage sits between the check-in agent's `escalate_to_nurse` call and the nurse queue. The check-in agent still escalates exactly as it does today, placing the message in the nurse queue; triage does not change that step. Triage then reads pending items from that same queue with `pending_messages`, assigns a tier with `tier_message`, and forwards each item with `route_message`. Nothing reaches a nurse, admin, or an auto-reply without passing through triage's tiering and routing step.

## Why
Every escalation from check-in currently lands in one undifferentiated nurse queue, so urgent clinical messages wait behind routine refill requests and non-clinical questions (e.g., billing, scheduling, portal access). Triage reads each pending message, assigns exactly one tier — `urgent_clinical`, `non_urgent_clinical`, or `non_clinical` — and routes it accordingly: `urgent_clinical` to `nurse_urgent`, `non_urgent_clinical` (including prescription refills) to `nurse_routine`, and `non_clinical` to either `admin` or `auto_reply`, always with a draft reply attached for the nurse to review before it goes out. The goal is to get urgent items in front of a nurse faster and get non-clinical volume out of the clinical queue entirely, without ever having triage reply to a patient unsupervised.

Evidence from the queue log: 2401 escalations a week, median nurse response 29.6 hours (p90 72.9), 40% of the nurse queue is non-clinical, 344 escalations unanswered over 24 hours from 342 patients.

## Tools it needs
- `pending_messages`
- `tier_message`
- `route_message`

## Decisions a human must make before it goes live
1. Urgent thresholds: the systolic and diastolic blood pressure, the low and high glucose, and the symptom words that are always urgent.
2. Non-clinical handling: route to admin staff, auto-reply from approved content, or hold for the morning.
3. After-hours rule: what happens to an urgent message at 1:48am when no nurse is on shift.
4. Consent: whether 'don't tell the doctor' is honoured, and what the patient is told either way.

## Acceptance test
Run the fifteen night texts in Exhibit E through the rendered prompt and score each one against the nurse's key (`northline/agents/triage/nurse_key.json`). Two kinds of failure are marked: **MISS**, the tier does not match the key; **MISROUTED**, the tier matched but an urgent message was not sent to `nurse_urgent`. The run reports accuracy across all fifteen, urgent recall (the share of the key's urgent messages the agent kept urgent), the missed-urgent list, and the share of non-clinical messages routed away from nurses.

**The test does not block the deployment.** Its three numbers (urgent recall, non-clinical share routed away, and the fixed routine-time factor) are what the company model is told about the agent, so a miss in the test becomes a count of missed urgent cases on the dashboard, every week, for as long as the decision stands. The person deploying sees every miss, with the message and the nurse's note, and chooses: deploy as is, or change a decision and re-test. A clean run with Northline's default thresholds passes 15/15; loosening a threshold is what produces misses.

## Metrics it should move
- Median nurse response time (currently 29.6h)
- Share of nurse-queue items that are non-clinical (currently 40%)
- Count of escalations unanswered after 24h (currently 344/week)
- Time-to-first-response specifically for urgent_clinical-tiered items

## Risks
The most serious risk is downgrading a genuinely urgent case to `non_urgent_clinical` or `non_clinical`, delaying care; this risk cannot be fully eliminated by tiering logic alone, which is why every routed message — including `auto_reply` — carries a draft for human review rather than being sent automatically. A related risk is misclassifying clinical-but-routine messages (e.g., prescription refills) as `non_clinical`, which would route them to `admin`/`auto_reply` and strip them of clinical review entirely; refills must always tier as `non_urgent_clinical`. Because there is only one tier per message, ambiguous or multi-issue texts (a refill request that also mentions new symptoms) force a single choice — the system should bias toward the more clinically severe tier when a message is ambiguous. Volume patterns (e.g., true clinical emergencies arriving overnight, as in Exhibit E) may differ from daytime patterns the tiering was tuned on, so night-time performance needs explicit scrutiny rather than assumed parity. Finally, because Exhibit E's scoring only informs the deployer rather than gating deployment, there is a risk of proceeding despite a poor score if that signal isn't weighted seriously in the go/no-go call.

## Decision
- [ ] Approve: `/northline-deploy triage`
- [ ] Reject, reason:
