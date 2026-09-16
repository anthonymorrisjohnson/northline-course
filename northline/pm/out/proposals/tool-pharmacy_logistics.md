# Expansion proposal: `pharmacy_logistics`

**Kind:** tool  **Persona(s):** rural chronic-care patient on SMS, on-call nurse receiving escalation, community health worker or NEMT coordinator  **Evidence:** 19 conversations (16% of patient conversations)

## What users asked for
User needed medication refill and transportation to pharmacy but lacked access.

Example quotes:
- "That's the problem. I've been out of lisinopril for three days. My truck's been in the shop and the pharmacy is 45 miles away."
- "pharmacy says they need a new script before they'll refill it and the nearest one is 45 miles from me. Almost out."
- "I'm almost out of my lisinopril and the pharmacy told me they need a brand new prescription, not just a refill authorization. Problem is that pharmacy is 40 miles out and I don't have a ride lined up."

## Proposed tool
**Docstring (what the model reads):** Coordinates prescription-and-transport barriers by escalating the clinical need to the on-call nurse with full context and simultaneously queuing a transportation assistance request, so neither track stalls waiting for the other.

**Input schema:**
```json
{
  "type": "object",
  "required": [
    "patient_id",
    "medication_name",
    "days_supply_remaining",
    "prescription_barrier",
    "pharmacy_distance_miles",
    "transportation_available"
  ],
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Unique patient identifier."
    },
    "medication_name": {
      "type": "string",
      "description": "Name of the medication the patient is trying to obtain."
    },
    "days_supply_remaining": {
      "type": "integer",
      "minimum": 0,
      "description": "Patient-reported doses or days of medication left. Drives clinical urgency triage."
    },
    "prescription_barrier": {
      "type": "string",
      "enum": [
        "new_script_required",
        "refill_authorization_only",
        "prior_auth_pending",
        "unknown"
      ],
      "description": "What the pharmacy says is blocking the fill. Determines what the nurse needs to act on."
    },
    "pharmacy_name": {
      "type": "string",
      "description": "Name of the pharmacy the patient uses (optional but aids nurse lookup)."
    },
    "pharmacy_distance_miles": {
      "type": "number",
      "minimum": 0,
      "description": "Approximate distance in miles from patient to pharmacy. Flags rural transport need."
    },
    "transportation_available": {
      "type": "boolean",
      "description": "Whether the patient currently has a way to reach the pharmacy."
    },
    "preferred_contact_window": {
      "type": "string",
      "description": "Optional. Patient's preferred time to be reached (e.g., 'mornings', 'after 2pm')."
    },
    "additional_context": {
      "type": "string",
      "maxLength": 500,
      "description": "Optional free-text from the patient's message for the nurse's review."
    }
  }
}
```

**Nearest existing tool(s):** escalate_to_nurse, log_reading

## What the backend needs
Two parallel writes on tool invocation:

1. **Nurse escalation queue** — creates an `escalate_to_nurse` task pre-populated with medication name, days remaining, prescription barrier, pharmacy name, and patient contact window. If `days_supply_remaining` ≤ 3, the task is flagged `priority: urgent`. The nurse sees everything needed to call the pharmacy and authorize/write a script without a separate lookup.

2. **Transportation coordination service** — if `transportation_available` is `false`, enqueues a transport assistance request (NEMT broker API, volunteer driver network, or community health worker dispatch — whichever is configured per region). Payload includes patient_id, pharmacy name, distance, and a reference to the open nurse task so transport timing can be coordinated once the script is cleared.

## Safety notes
1. **No clinical advice through this tool.** The tool never tells the patient whether, when, or how to take medication, nor does it comment on whether the refill is appropriate. All prescription decisions flow exclusively through the nurse.

2. **Urgency gate.** `days_supply_remaining` ≤ 3 must set `priority: urgent` on the nurse task. The SMS agent must not imply to the patient that the situation is routine when this flag is active.

3. **Transport does not gate clinical action.** The nurse escalation fires immediately regardless of whether transport can be arranged. Transportation is a parallel track, never a prerequisite.

4. **Confirmation to patient is non-clinical.** The only message returned to the SMS agent for the patient is: confirmation that a nurse has been notified and that transport assistance is being arranged (if applicable). No medication guidance, no estimated timelines for the script.

5. **Audit trail.** Both the nurse task and the transport request must reference the same `patient_id` and a shared `case_id` so outcomes can be linked in the care record.

## Decision
- [ ] Approve: `/expand tool-pharmacy_logistics`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
