# Expansion proposal: `insurance_question`

**Kind:** tool  **Persona(s):** SMS check-in agent (creates the tool call), Care navigator (receives and works the queued task), On-call nurse (receives critical-urgency pages and flagged clinical questions)  **Evidence:** 21 conversations (17% of patient conversations)

## What users asked for
Patient asked for help with insurance prior authorization for medication refill.

Example quotes:
- "Any chance you can help with a prior auth? Insurance has been holding up my metoprolol refill for a week now."
- "Yeah, I'm almost out of my lisinopril and my insurance has been rejecting the refill for two weeks. Any chance you can sort that out?"
- "My insurance denied my test strips last week so I've only been checking every few days."

## Proposed tool
**Docstring (what the model reads):** Capture a patient's insurance or prior-authorization question and route it to a care-team navigator — never dispenses clinical advice, never promises outcomes, and always closes with a human callback.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Unique patient identifier"
    },
    "question_text": {
      "type": "string",
      "description": "Verbatim or lightly normalised text of the patient's insurance question"
    },
    "medication_or_supply": {
      "type": "string",
      "description": "Drug name, device, or supply at issue (e.g. 'metoprolol 50 mg', 'test strips'); empty string if not applicable"
    },
    "days_until_exhausted": {
      "type": "integer",
      "description": "Patient-reported days of supply remaining; null if unknown",
      "minimum": 0
    },
    "urgency": {
      "type": "string",
      "enum": [
        "routine",
        "urgent",
        "critical"
      ],
      "description": "Derived from days_until_exhausted: >7 days = routine, 2\u20137 = urgent, <2 = critical"
    },
    "prior_denial": {
      "type": "boolean",
      "description": "True if the patient states the insurer has already denied the claim at least once"
    }
  },
  "required": [
    "patient_id",
    "question_text",
    "urgency"
  ]
}
```

**Nearest existing tool(s):** log_reading, next_checkin

## What the backend needs
Care navigation queue (not the SMS agent's own DB). On call: writes a task to the care-team task system with patient_id, urgency, medication_or_supply, days_until_exhausted, and question_text; triggers an automated acknowledgement SMS to the patient ("A care navigator will contact you within [X hours]"); for critical urgency also pages the on-call nurse directly. Does not touch payer APIs, does not submit PAs on behalf of the practice — that remains a human workflow.

## Safety notes
1. No clinical advice path: the tool must never recommend dose changes, substitutions, or clinical workarounds for a denied medication — if question_text contains clinical language, the routing note to the nurse must flag it explicitly. 2. No outcome promises: the SMS acknowledgement must not say 'we will get this approved' — only that the team will follow up. 3. Urgency escalation: days_until_exhausted ≤ 1 must page a nurse synchronously, not just queue a task, because a gap in a critical medication (cardiac, diabetes) is a patient-safety event. 4. PII handling: question_text is stored in the care-team system under the same access controls as clinical notes — not logged to general application logs. 5. Scope boundary: this tool handles administrative/coverage questions only; any question that is primarily 'what should I take instead?' must be routed to nurse triage, not answered inline.

## Decision
- [ ] Approve: `/expand tool-insurance_question`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
