# Expansion proposal: `pharmacy_logistics`

**Kind:** tool  **Persona(s):** patient, plan  **Evidence:** 19 conversations (16% of patient conversations)

## What users asked for
User needed medication refill and transportation to pharmacy but lacked access.

Example quotes:
- "That's the problem. I've been out of lisinopril for three days. My truck's been in the shop and the pharmacy is 45 miles away."
- "pharmacy says they need a new script before they'll refill it and the nearest one is 45 miles from me. Almost out."
- "I'm almost out of my lisinopril and the pharmacy told me they need a brand new prescription, not just a refill authorization. Problem is that pharmacy is 40 miles out and I don't have a ride lined up."

## Proposed tool
**Docstring (what the model reads):** Capture a patient's medication-access barrier—combining prescription status and transportation gap—then either coordinate non-emergency transport and pharmacy transfer directly or, when a new prescription is required, escalate to the on-call nurse with full context before any pharmacy action is taken.

**Input schema:**
```json
{
  "type": "object",
  "required": [
    "patient_id",
    "medication_name",
    "days_supply_remaining",
    "prescription_required",
    "transportation_barrier"
  ],
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Northline Care patient identifier"
    },
    "medication_name": {
      "type": "string",
      "description": "Name of the medication the patient is trying to obtain (e.g., 'lisinopril 10mg')"
    },
    "days_supply_remaining": {
      "type": "integer",
      "minimum": 0,
      "description": "Estimated days of medication supply left; drives urgency tier (0\u20133 = same-day SLA)"
    },
    "prescription_required": {
      "type": "boolean",
      "description": "True when the pharmacy requires a new prescription before dispensing; triggers mandatory nurse escalation"
    },
    "transportation_barrier": {
      "type": "boolean",
      "description": "True when the patient lacks reliable transport to their current pharmacy"
    },
    "distance_to_pharmacy_miles": {
      "type": "number",
      "description": "Approximate miles from patient to their current pharmacy; used to triage NEMT vs mail-order vs closer-pharmacy options"
    },
    "preferred_contact_window": {
      "type": "string",
      "description": "Patient's preferred callback or coordination window (e.g., 'morning', 'after 2pm')"
    }
  }
}
```

**Nearest existing tool(s):** escalate_to_nurse, log_reading

## What the backend needs
Three backend integrations are required: (1) **Nurse escalation queue** (existing `escalate_to_nurse` backend) — receives a pre-populated context bundle (patient_id, medication, days_supply_remaining, prescription_required=true) whenever a new Rx is needed, so the nurse can send an e-prescription to an alternate pharmacy without the patient calling the office; (2) **NEMT broker API** (e.g., Ride Health or MTM) — dispatches a non-emergency medical transport ride when transportation_barrier=true and the prescription path is clear; (3) **Pharmacy network locator** — queries for pharmacies closer than the patient's current one and checks mail-order eligibility, feeding the nurse or NEMT booking with the correct destination before any ride is confirmed.

## Safety notes
1. **Prescription-required always routes to nurse first.** When `prescription_required=true`, the tool must call `escalate_to_nurse` with the full context bundle before triggering any NEMT or pharmacy-transfer action. No pharmacy coordination begins until a nurse acknowledges. 2. **No clinical advice through the tool.** The tool collects logistics facts only; it never suggests, confirms, adjusts, or comments on the medication, dose, or treatment plan. Medication questions surfaced during intake are forwarded verbatim to the nurse. 3. **Days-supply urgency floor.** `days_supply_remaining` ≤ 3 must set escalation priority to `urgent` in the nurse queue, mirroring the existing urgent-threshold logic. 4. **Patient confirmation before transport booking.** NEMT dispatch is not triggered until the patient confirms the destination pharmacy and appointment window via SMS reply, preventing unwanted bookings. 5. **Audit log.** Every tool invocation must be written to the care record (via `log_reading` backend convention) so the supervising nurse has a complete interaction trail.

## Decision
- [ ] Approve: `/expand tool-pharmacy_logistics`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
