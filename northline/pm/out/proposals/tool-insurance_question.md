# Expansion proposal: `insurance_question`

**Kind:** tool  **Persona(s):** patient, plan  **Evidence:** 21 conversations (17% of patient conversations)

## What users asked for
User needed help with insurance prior authorization for medication refill.

Example quotes:
- "Any chance you can help with a prior auth? Insurance has been holding up my metoprolol refill for a week now."
- "My insurance denied my test strips last week so I've only been checking every few days."
- "My insurance denied my test strip claim and I'm basically out now. Haven't been able to check my blood sugar in a couple days."

## Proposed tool
**Docstring (what the model reads):** Capture a patient's insurance barrier (prior authorization, denial, or supply gap), triage urgency based on days-without-medication/supplies, and route to care coordination for administrative follow-up or to an on-call nurse when the patient is currently going without a critical medication or monitoring supply.

**Input schema:**
```json
{
  "type": "object",
  "required": [
    "patient_id",
    "issue_type",
    "item_name"
  ],
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Unique patient identifier from the SMS session"
    },
    "issue_type": {
      "type": "string",
      "enum": [
        "prior_auth",
        "claim_denial",
        "formulary",
        "cost_barrier",
        "other"
      ],
      "description": "Category of insurance barrier the patient is facing"
    },
    "item_name": {
      "type": "string",
      "description": "Medication or supply held up (e.g., metoprolol, test strips)"
    },
    "days_without": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of days patient has been without the item; null if still has supply"
    },
    "insurance_name": {
      "type": "string",
      "description": "Name of the insurance plan, if patient provided it"
    },
    "patient_message_verbatim": {
      "type": "string",
      "description": "Exact SMS text from the patient describing the issue, preserved for downstream context"
    }
  }
}
```

**Nearest existing tool(s):** log_reading, next_checkin

## What the backend needs
Care coordination platform (e.g., Healthie or equivalent) to create a task assigned to the prior-auth specialist; EHR write-back to flag the open insurance issue on the patient chart; nurse escalation queue triggered automatically when days_without > 0 for any medication classified as chronic-disease-critical (antihypertensives, insulin, glucose monitoring supplies).

## Safety notes
1. The tool never returns insurance coverage determinations, clinical guidance, or dosing advice to the patient — the SMS response is always a warm handoff message (e.g., "I've flagged this for our care team; someone will call you within one business day"). 2. If days_without > 0 AND item_name matches the patient's active chronic-disease medication or monitoring supply list, the tool must simultaneously create a nurse escalation task (same-business-day callback) alongside the administrative task — the patient going without critical supplies is a clinical safety event, not just a billing issue. 3. patient_message_verbatim must be passed to every downstream task so the nurse or coordinator has the patient's own words, not a paraphrase. 4. No PHI from this tool's output is returned to the SMS thread beyond a confirmation message.

## Decision
- [ ] Approve: `/northline-expand tool-insurance_question`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
