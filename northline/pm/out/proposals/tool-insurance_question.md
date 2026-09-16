# Expansion proposal: `insurance_question`

**Kind:** tool  **Persona(s):** care coordinator, on-call nurse  **Evidence:** 20 conversations (17% of patient conversations)

## What users asked for
Patient needs help with insurance prior authorization for medication refill

Example quotes:
- "any chance you can help with a prior auth? Insurance has been holding up my metoprolol refill for a week now."
- "I'm almost out of my lisinopril and my insurance has been rejecting the refill for two weeks."
- "My insurance denied my test strips last week so I've only been checking every few days."

## Proposed tool
**Docstring (what the model reads):** Captures a patient's insurance or prior authorization barrier for a medication or supply, then routes it to the care coordination queue — or directly to the on-call nurse if the patient reports critically low days of supply remaining.

**Input schema:**
```json
{
  "type": "object",
  "required": [
    "patient_id",
    "medication_or_supply",
    "issue_type",
    "patient_description"
  ],
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Northline Care patient identifier"
    },
    "medication_or_supply": {
      "type": "string",
      "description": "Name of the medication or supply affected (e.g., 'metoprolol 25mg', 'test strips')"
    },
    "issue_type": {
      "type": "string",
      "enum": [
        "prior_authorization",
        "coverage_denial",
        "refill_delay",
        "unknown"
      ],
      "description": "Category of insurance barrier as understood from the patient's message"
    },
    "patient_description": {
      "type": "string",
      "description": "Verbatim or close-paraphrase of what the patient said, preserved for the nurse or coordinator"
    },
    "days_of_supply_remaining": {
      "type": "integer",
      "minimum": 0,
      "description": "Estimated days of medication or supply the patient has left; null if patient did not specify"
    }
  }
}
```

**Nearest existing tool(s):** log_reading, next_checkin

## What the backend needs
Care Coordination Queue API (creates a task for a care coordinator to work the prior auth) + Nurse Escalation API (pages the on-call nurse with full context when days_of_supply_remaining is ≤ 3 or null and issue has been ongoing > 7 days) + EHR read (pulls current prescription and last fill date so the nurse or coordinator has context without asking the patient again)

## Safety notes
1. The tool NEVER tells the patient whether to take, skip, or substitute a medication — any clinical question surfaces as a nurse escalation, not a tool response. 2. If days_of_supply_remaining ≤ 3 (or the patient says they are already rationing), the call goes to the nurse queue immediately, not the coordinator queue — rationing chronic-disease medication (beta-blockers, ACE inhibitors, insulin supplies) is a safety event. 3. The patient-facing confirmation is administrative only: 'We've flagged this for your care team — someone will follow up within [SLA].' 4. Patient description is stored verbatim to avoid lossy summarization before the nurse sees it. 5. Tool does not attempt to contact the insurer directly or provide prior auth form guidance; that action belongs to the coordinator workflow triggered downstream.

## Decision
- [ ] Approve: `/expand tool-insurance_question`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
