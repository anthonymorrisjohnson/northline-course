# Expansion proposal: `request_refill`

**Kind:** tool  **Persona(s):** SMS check-in agent (initiates the tool call mid-conversation), Nurse coordinator (receives the routed task in the EHR queue)  **Evidence:** 12 conversations (10% of patient conversations)

## What users asked for
Patient requested medication refill but assistant cannot process refills directly.

Example quotes:
- "While I'm waiting can you at least send in a refill on my lisinopril? I'm running low."
- "Getting a little low on it though — can you do a refill request? And I don't suppose you can just talk for a bit."
- "And I'm out of refills."

## Proposed tool
**Docstring (what the model reads):** Capture a patient's medication refill request with urgency context and route it to the care team for nurse or prescriber review before any pharmacy action is taken.

**Input schema:**
```json
{
  "type": "object",
  "required": [
    "patient_id",
    "medication_name",
    "urgency"
  ],
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Stable patient identifier from the active session."
    },
    "medication_name": {
      "type": "string",
      "description": "Medication the patient named, transcribed verbatim \u2014 no normalization or inference by the agent."
    },
    "urgency": {
      "type": "string",
      "enum": [
        "running_low",
        "out_of_medication"
      ],
      "description": "running_low = patient reports a few doses remaining; out_of_medication = patient reports zero doses on hand."
    },
    "patient_note": {
      "type": "string",
      "description": "Optional verbatim patient quote providing context (e.g., 'I'm out of refills'). Preserved for the reviewing nurse."
    }
  },
  "additionalProperties": false
}
```

**Nearest existing tool(s):** log_reading, escalate_to_nurse

## What the backend needs
EHR task queue (creates a typed refill-request task linked to the patient chart) + the same nurse-alert pathway used by escalate_to_nurse, distinguished by task_type=refill_request. urgency=out_of_medication should trigger a same-day SLA; urgency=running_low can queue for next business day. No direct pharmacy or e-prescribing write access — the tool is append-only to the task queue.

## Safety notes
1. No pharmacy write access: the tool never transmits to a pharmacy system; all refills require nurse or prescriber approval before dispensing.
2. No clinical inference: the agent must not validate, substitute, or comment on the medication name — pass it through verbatim.
3. out_of_medication urgency requires same-day nurse review; implement an SLA alert if unacknowledged after 4 hours.
4. On tool success, the agent confirms to the patient only that "your request has been sent to your care team" — never confirms the refill will be approved or dispensed.
5. If medication_name is blank or patient is ambiguous, fall back to escalate_to_nurse with the raw transcript rather than invoking this tool with incomplete data.

## Decision
- [ ] Approve: `/expand tool-request_refill`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
