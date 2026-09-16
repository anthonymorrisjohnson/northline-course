# Expansion proposal: `request_refill`

**Kind:** tool  **Persona(s):** patient  **Evidence:** 12 conversations (10% of patient conversations)

## What users asked for
Patient requested medication refill but assistant cannot process refills directly.

Example quotes:
- "While I'm waiting can you at least send in a refill on my lisinopril? I'm running low."
- "Getting a little low on it though — can you do a refill request? And I don't suppose you can just talk for a bit."
- "And I'm out of refills."

## Proposed tool
**Docstring (what the model reads):** Submit a medication refill request on behalf of a patient to the prescribing provider via the EHR e-prescribing workflow, and escalate to a nurse if the medication requires clinical review before reordering.

**Input schema:**
```json
{
  "type": "object",
  "required": [
    "patient_id",
    "medication_name"
  ],
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Northline patient identifier"
    },
    "medication_name": {
      "type": "string",
      "description": "Name of the medication the patient is requesting a refill for, as stated by the patient"
    },
    "days_supply_remaining": {
      "type": "integer",
      "description": "Patient-reported days of supply remaining; omit if unknown",
      "minimum": 0
    },
    "patient_note": {
      "type": "string",
      "description": "Verbatim or paraphrased context from the patient (e.g. 'running low', 'out of refills') to include in the clinical handoff"
    }
  },
  "additionalProperties": false
}
```

**Nearest existing tool(s):** log_reading, escalate_to_nurse

## What the backend needs
EHR e-prescribing API (Surescripts-connected, e.g. Epic MyChart Refill Request or PointClickCare Rx module) — creates a pending refill task on the prescriber's worklist; falls back to calling `escalate_to_nurse` with full context when the EHR returns a rejection code (controlled substance, no active Rx, prior-auth required, or any 4xx).

## Safety notes
1. The agent must never tell the patient whether the refill will be approved or denied — all clinical judgment stays with the prescriber or nurse. 2. If the EHR rejects the request for any reason (controlled substance flag, expired prescription, prior-auth hold), the tool must automatically call `escalate_to_nurse` with `patient_id`, `medication_name`, `patient_note`, and the rejection code — the patient receives only "I've flagged this for your care team." 3. `days_supply_remaining` ≤ 3 should set escalation urgency to `urgent` in the nurse handoff. 4. The tool must not suggest dose changes, substitutions, or alternative medications under any circumstance.

## Decision
- [ ] Approve: `/expand tool-request_refill`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
