# Expansion proposal: `pharmacy_logistics`

**Kind:** tool  **Persona(s):** patient, plan  **Evidence:** 16 conversations (13% of patient conversations)

## What users asked for
User needed pharmacy access and transportation to obtain missing lisinopril medication.

Example quotes:
- "I've been out of lisinopril for three days. My truck's been in the shop and the pharmacy is 45 miles away."
- "pharmacy says they need a new script before they'll refill it and the nearest one is 45 miles from me. Almost out."
- "pharmacy told me they need a brand new prescription, not just a refill authorization. Problem is that pharmacy is 40 miles out and I don't have a ride lined up."

## Proposed tool
**Docstring (what the model reads):** Captures a patient's medication access barrier — including prescription status, distance, and transport availability — then routes to a nurse with full context and queues NEMT or pharmacy-delivery coordination as appropriate.

**Input schema:**
```json
{
  "type": "object",
  "required": [
    "patient_id",
    "medication_name",
    "prescription_status",
    "pharmacy_distance_miles",
    "transport_available"
  ],
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Unique patient identifier"
    },
    "medication_name": {
      "type": "string",
      "description": "Name of the medication the patient cannot obtain"
    },
    "days_without_medication": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of days the patient has been without this medication; drives nurse urgency tier"
    },
    "prescription_status": {
      "type": "string",
      "enum": [
        "has_valid_script",
        "needs_new_script",
        "needs_refill_auth"
      ],
      "description": "Current state of the prescription; any value other than has_valid_script triggers nurse escalation"
    },
    "pharmacy_distance_miles": {
      "type": "number",
      "minimum": 0,
      "description": "Estimated miles to the nearest in-network pharmacy"
    },
    "transport_available": {
      "type": "boolean",
      "description": "Whether the patient has reliable transportation today"
    },
    "preferred_resolution": {
      "type": "string",
      "enum": [
        "mail_delivery",
        "nemt_ride",
        "pharmacy_transfer",
        "nurse_callback"
      ],
      "description": "Patient's preferred logistics path; nurse may adjust based on clinical urgency"
    },
    "patient_notes": {
      "type": "string",
      "maxLength": 500,
      "description": "Free-text context from the patient (e.g., truck in shop, caregiver unavailable)"
    }
  }
}
```

**Nearest existing tool(s):** log_medication, escalate_to_nurse

## What the backend needs
Three integrations required: (1) **Nurse escalation queue** — any call where `prescription_status != "has_valid_script"` or `days_without_medication >= 3` must enqueue a nurse callback with the full payload before any logistics step proceeds; (2) **NEMT / rideshare broker API** (e.g., Ride Health, National MedTrans Network) — to request a non-emergency medical transport ride when `transport_available = false` and prescription is in hand or resolved; (3) **Pharmacy partner API** (e.g., RelayHealth, SureScripts) — to request mail-order dispatch or nearest-pharmacy transfer once a valid script exists.

## Safety notes
1. **Clinical gate first**: If `prescription_status` is `needs_new_script` or `needs_refill_auth`, the tool must escalate to a nurse with the complete payload before initiating any logistics action — the tool never tells the patient how to obtain or renew a prescription. 2. **Urgency scoring**: `days_without_medication >= 3` for a cardiovascular or chronic-disease medication (e.g., lisinopril, metformin) must set nurse priority to URGENT and target a ≤2-hour callback SLA. 3. **No clinical promises via SMS**: Confirmation messages to the patient must be limited to logistics status ("A nurse will call you within 2 hours" or "A ride has been requested") — never medication guidance, dosing advice, or prescription timelines. 4. **HIPAA**: Pharmacy name, medication, and distance fields constitute PHI in combination; payloads to NEMT and pharmacy APIs must be transmitted over encrypted channels with minimum-necessary data. 5. **Fallback**: If NEMT booking fails, the tool must re-escalate to the nurse rather than leaving the patient without a resolution path.

## Decision
- [ ] Approve: `/northline-expand tool-pharmacy_logistics`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
