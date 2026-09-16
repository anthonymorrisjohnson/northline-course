# Expansion proposal: `request_refill`

**Kind:** tool  **Persona(s):** patient, plan  **Evidence:** 14 conversations (12% of patient conversations)

## What users asked for
Patient needed medication refill coordination and transportation assistance to a remote pharmacy.

Example quotes:
- "Yeah, I'm almost out of my lisinopril and my insurance has been rejecting the refill for two weeks."
- "While I'm waiting can you at least send in a refill on my lisinopril? I'm running low."
- "Getting a little low on it though — can you do a refill request? And I don't suppose you can just talk for a bit."

## Proposed tool
**Docstring (what the model reads):** Submits a medication refill coordination request on behalf of the patient and automatically escalates to the on-call nurse — with full context — when supply is critically low, insurance has rejected the refill, or any clinical judgment is required.

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
      "description": "Unique patient identifier from the EHR."
    },
    "medication_name": {
      "type": "string",
      "description": "Name of the medication the patient is requesting a refill for, as stated by the patient."
    },
    "days_supply_remaining": {
      "type": "integer",
      "minimum": 0,
      "description": "Patient's self-reported estimate of days of medication remaining. Values \u22647 trigger urgent nurse escalation."
    },
    "insurance_rejection": {
      "type": "boolean",
      "description": "True if the patient reports the insurer has denied a prior refill attempt. Always triggers nurse escalation for prior-authorization review."
    },
    "transportation_needed": {
      "type": "boolean",
      "description": "True if the patient cannot reach the pharmacy without assistance. Routes a care-coordination flag alongside the refill request."
    },
    "preferred_pharmacy_id": {
      "type": "string",
      "description": "Optional identifier for the patient's preferred or nearest pharmacy from the pharmacy directory."
    },
    "patient_note": {
      "type": "string",
      "maxLength": 500,
      "description": "Verbatim or lightly cleaned patient statement to be forwarded as context to the nurse or care coordinator."
    }
  }
}
```

**Nearest existing tool(s):** log_reading, escalate_to_nurse

## What the backend needs
EHR/ePrescribing API (e.g., Surescripts) for refill request submission; insurance prior-authorization workflow API for rejection triage; internal care-coordination platform for transportation dispatch; `escalate_to_nurse` as a downstream call whenever `insurance_rejection` is true or `days_supply_remaining` ≤ 7.

## Safety notes
1. This tool performs administrative coordination only — it never confirms, denies, or adjusts the clinical appropriateness of any medication. 2. Any `insurance_rejection: true` or `days_supply_remaining` ≤ 7 MUST trigger an immediate call to `escalate_to_nurse`, passing `medication_name`, `days_supply_remaining`, `insurance_rejection`, and `patient_note` as context so the nurse can act without re-interviewing the patient. 3. The SMS response to the patient must not include dosing guidance, therapeutic alternatives, or any language that could be construed as clinical advice — it is limited to confirming the request was received and that a nurse will follow up if escalation fired. 4. `patient_note` must be treated as free text from an unverified source and must not be relayed to third-party systems without PHI-handling compliance checks.

## Decision
- [ ] Approve: `/expand tool-request_refill`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
