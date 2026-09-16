# Expansion proposal: `pharmacy_logistics`

**Kind:** tool  **Persona(s):** care_coordinator, nurse (on escalation when medication_urgency_flag is true)  **Evidence:** 17 conversations (14% of patient conversations)

## What users asked for
Patient requested delivery arrangements and transportation coverage for pharmacy pickup.

Example quotes:
- "Any way to set up a delivery or get a ride covered through this program?"
- "Problem is that pharmacy is 40 miles out and I don't have a ride lined up."
- "Is there any way you can get me a ride to the clinic in Minot?"

## Proposed tool
**Docstring (what the model reads):** Coordinates non-emergency pharmacy delivery or transportation coverage for patients who cannot reach their pharmacy independently, escalating to a nurse if the request involves clinical judgment about medication urgency or care continuity.

**Input schema:**
```json
{
  "type": "object",
  "required": [
    "patient_id",
    "request_type"
  ],
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Unique patient identifier from the care platform"
    },
    "request_type": {
      "type": "string",
      "enum": [
        "delivery",
        "transportation"
      ],
      "description": "Whether the patient needs medication delivered to them or a ride to the pharmacy or clinic"
    },
    "pharmacy_name": {
      "type": "string",
      "description": "Name of the patient's pharmacy, if known"
    },
    "pharmacy_address": {
      "type": "string",
      "description": "Full address of the pharmacy or clinic destination"
    },
    "estimated_distance_miles": {
      "type": "number",
      "description": "Approximate one-way distance in miles, if patient provided it"
    },
    "preferred_date": {
      "type": "string",
      "format": "date",
      "description": "Patient's preferred date for delivery or ride, ISO 8601"
    },
    "medication_urgency_flag": {
      "type": "boolean",
      "description": "True if patient indicated they are running low or out of medication \u2014 triggers nurse escalation"
    },
    "patient_notes": {
      "type": "string",
      "description": "Verbatim or paraphrased patient statement about the logistics barrier, for context"
    }
  }
}
```

**Nearest existing tool(s):** log_reading, escalate_to_nurse

## What the backend needs
NEMT (Non-Emergency Medical Transportation) broker API for ride coverage — e.g., Modivcare or LogistiCare — plus a pharmacy delivery coordination service (direct pharmacy partner or third-party courier). Requires read access to the patient's insurance/benefit eligibility record to confirm covered services before booking. Falls back to the care-coordination queue if no eligible benefit exists.

## Safety notes
1. No clinical advice is ever returned to the patient through this tool. 2. If `medication_urgency_flag` is true (patient is out of or critically low on medication), the tool must call `escalate_to_nurse` with the full request context rather than attempting logistics resolution autonomously — the nurse determines whether a gap in medication constitutes a clinical risk. 3. The tool confirms patient identity via `patient_id` before accessing benefit records or booking any service. 4. Booking confirmation is sent to the patient via SMS and simultaneously logged against their care record for nurse visibility. 5. The tool never stores pharmacy names or addresses beyond the current transaction without explicit consent.

## Decision
- [ ] Approve: `/expand tool-pharmacy_logistics`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
