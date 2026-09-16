# Expansion proposal: `request_refill`

**Kind:** tool  **Persona(s):** SMS check-in agent (caller), on-call nurse (recipient of the queued task), prescribing provider (contacted by nurse offline)  **Evidence:** 11 conversations (9% of patient conversations)

## What users asked for
Patient requested medication refill but agent cannot process refills.

Example quotes:
- "I've been out of lisinopril for three days. My truck's been in the shop and the pharmacy is 45 miles away."
- "pharmacy says they need a new script before they'll refill it and the nearest one is 45 miles from me. Almost out."
- "I'm almost out of my lisinopril and the pharmacy told me they need a brand new prescription, not just a refill authorization."

## Proposed tool
**Docstring (what the model reads):** Capture a patient's medication refill request and route it as a structured task to the nurse queue so a clinician can coordinate with the prescribing provider and pharmacy — the agent never authorizes refills.

**Input schema:**
```json
{
  "type": "object",
  "required": [
    "patient_id",
    "medication_name",
    "days_supply_remaining"
  ],
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Northline Care patient identifier"
    },
    "medication_name": {
      "type": "string",
      "description": "Name of the medication the patient reports needing (as stated by patient, not validated)"
    },
    "days_supply_remaining": {
      "type": "integer",
      "minimum": 0,
      "description": "Patient-reported days of medication remaining; 0 means currently out"
    },
    "pharmacy_name": {
      "type": "string",
      "description": "Pharmacy the patient uses, if provided"
    },
    "pharmacy_phone": {
      "type": "string",
      "description": "Pharmacy phone number, if provided"
    },
    "patient_notes": {
      "type": "string",
      "description": "Verbatim or close-paraphrase of what the patient said about barriers (transport, prior auth, etc.)"
    }
  }
}
```

**Nearest existing tool(s):** log_reading, escalate_to_nurse

## What the backend needs
Nurse task queue (same system backing escalate_to_nurse). Creates a pre-populated refill task with structured fields so the on-call nurse can call the pharmacy and contact the prescribing provider without re-interviewing the patient. When days_supply_remaining is 0 or 1, the task is flagged urgent and surfaces at the top of the queue. The tool returns a confirmation token the agent can relay to the patient ("your nurse has been notified and will follow up within X hours").

## Safety notes
1. The tool never authorizes, denies, or opines on whether a refill is appropriate — that decision belongs to the prescriber. 2. The agent must not tell the patient the refill is approved or will be approved; the confirmation message must only confirm that a nurse has been notified. 3. days_supply_remaining = 0 must always trigger an urgent flag; do not suppress urgency even if a recent log_reading entry exists. 4. medication_name is stored as patient-reported text only — no drug database lookup or dosage inference by the agent. 5. If the patient describes symptoms alongside the refill request (e.g., elevated BP, chest tightness), the agent must call escalate_to_nurse directly instead of this tool, because that is a clinical situation requiring triage, not a refill queue task.

## Decision
- [ ] Approve: `/expand tool-request_refill`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
