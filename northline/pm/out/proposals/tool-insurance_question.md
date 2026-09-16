# Expansion proposal: `insurance_question`

**Kind:** tool  **Persona(s):** care coordinator, nurse  **Evidence:** 19 conversations (16% of patient conversations)

## What users asked for
User asked for help processing insurance prior authorization for medication refill.

Example quotes:
- "any chance you can help with a prior auth? Insurance has been holding up my metoprolol refill for a week now."
- "My insurance denied my test strips last week so I've only been checking every few days."
- "My insurance denied my test strip claim and I'm basically out now."

## Proposed tool
**Docstring (what the model reads):** Captures a patient's insurance or prior-authorization question and queues it for a care coordinator, supplying enough context to act without calling the patient back.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Northline patient identifier"
    },
    "question_text": {
      "type": "string",
      "description": "Patient's verbatim or close-paraphrase message about the insurance issue"
    },
    "medication_or_supply": {
      "type": "string",
      "description": "Drug name, device, or supply being denied or delayed (e.g. 'metoprolol 25 mg', 'test strips')"
    },
    "issue_type": {
      "type": "string",
      "enum": [
        "prior_auth",
        "claim_denial",
        "coverage_question",
        "other"
      ],
      "description": "Category of insurance barrier"
    },
    "days_without_supply": {
      "type": "integer",
      "description": "How many days the patient has been without the medication or supply; omit if unknown"
    },
    "insurance_carrier": {
      "type": "string",
      "description": "Insurer name as stated by the patient; omit if unknown"
    }
  },
  "required": [
    "patient_id",
    "question_text",
    "issue_type"
  ]
}
```

**Nearest existing tool(s):** log_reading, next_checkin

## What the backend needs
A care-coordination task queue (e.g. the existing EHR worklist or a lightweight ticket store) that can create a tagged task visible to nurses and care coordinators, pre-populated with the schema fields and a computed urgency flag (days_without_supply >= 3 → HIGH).

## Safety notes
No clinical advice ever — the tool acknowledges the patient and sets expectations only. If days_without_supply >= 3 for a cardiac or diabetes-critical supply, the task is flagged HIGH and surfaces immediately in the nurse queue. The tool queues human action only; it does not submit prior-auth requests, contact payers, or promise outcomes, keeping liability with credentialed staff.

## Decision
- [ ] Approve: `/expand tool-insurance_question`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
