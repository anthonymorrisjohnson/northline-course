# Expansion proposal: `insurance_question`

**Kind:** tool  **Persona(s):** patient, plan  **Evidence:** 19 conversations (16% of patient conversations)

## What users asked for
User asked for help processing insurance prior authorization for medication refill.

Example quotes:
- "any chance you can help with a prior auth? Insurance has been holding up my metoprolol refill for a week now."
- "My insurance denied my test strips last week so I've only been checking every few days."
- "My insurance denied my test strip claim and I'm basically out now."

## Proposed tool
**Docstring (what the model reads):** Capture a patient's insurance barrier (prior authorization, claim denial, or coverage question) and open a care-coordination task, escalating to a nurse when supply is critically low.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Northline patient identifier"
    },
    "issue_type": {
      "type": "string",
      "enum": [
        "prior_auth",
        "claim_denial",
        "coverage_question",
        "formulary_question"
      ],
      "description": "Category of insurance barrier"
    },
    "medication_or_supply": {
      "type": "string",
      "description": "Name of the medication or supply being denied or held"
    },
    "days_supply_remaining": {
      "type": "integer",
      "minimum": 0,
      "description": "Patient-reported days of supply on hand; drives escalation routing"
    },
    "free_text": {
      "type": "string",
      "description": "Patient's own words describing the situation, preserved verbatim for the care team"
    }
  },
  "required": [
    "patient_id",
    "issue_type",
    "free_text"
  ]
}
```

**Nearest existing tool(s):** log_reading, next_checkin

## What the backend needs
Care coordination / prior-auth tracking system: creates a task in the case management queue (EHR or standalone), optionally calls the payer's prior-auth API to prefill case details, and triggers a nurse alert via the clinical escalation pathway when days_supply_remaining is 0–2 or absent for a critical medication class.

## Safety notes
1. The tool never advises the patient on whether to skip, split, or substitute doses — any supply-gap guidance is a clinical decision routed to a nurse. 2. When days_supply_remaining <= 2 OR the medication_or_supply matches a high-risk class (insulin, beta-blockers, anticoagulants), the backend must page the on-call nurse with full context before confirming the task to the patient. 3. The SMS reply to the patient is administrative only: confirm the case was opened and give an expected callback window; no clinical content in the reply.

## Decision
- [ ] Approve: `/expand tool-insurance_question`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
