# Expansion proposal: `pharmacy_logistics`

**Kind:** tool  **Persona(s):** patient facing SMS check-in agent, nurse receiving escalation queue tasks, pharmacy logistics coordinator  **Evidence:** 19 conversations (16% of patient conversations)

## What users asked for
Patient in rural area needs mail pharmacy delivery and ride assistance; system cannot arrange transportation or logistics.

Example quotes:
- "even once the script is sent, the nearest pharmacy is like 45 minutes out. Is there any way to set up mail delivery or get help with a ride?"
- "Bigger issue is I'm almost out of lisinopril and my doctor said I need an actual new prescription this time, not just a refill. Pharmacy's a 45-minute drive one way."
- "Problem is the pharmacy is 40 miles from me and getting out there isn't easy."

## Proposed tool
**Docstring (what the model reads):** Arrange mail-order prescription delivery or non-emergency medical transportation to a pharmacy for patients facing distance or mobility barriers, and escalate to a nurse when the request involves a new prescription or any clinical question.

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
      "description": "Northline patient identifier"
    },
    "request_type": {
      "type": "string",
      "enum": [
        "mail_delivery",
        "ride_assistance",
        "both",
        "nurse_escalation"
      ],
      "description": "What the patient needs; use nurse_escalation when a new prescription or clinical question is detected"
    },
    "medication_names": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Medications the patient named; used to pre-populate the logistics order or nurse handoff"
    },
    "is_new_prescription": {
      "type": "boolean",
      "description": "True if the patient indicated they need a new prescription (not a refill); forces request_type to nurse_escalation"
    },
    "preferred_date": {
      "type": "string",
      "format": "date",
      "description": "Earliest acceptable delivery date or ride date (ISO 8601)"
    },
    "patient_address": {
      "type": "string",
      "description": "Delivery address for mail orders or pickup address for rides; pulled from record if omitted"
    },
    "pharmacy_name": {
      "type": "string",
      "description": "Patient's current pharmacy, if known"
    },
    "patient_note": {
      "type": "string",
      "description": "Verbatim or summarized patient context to include in the logistics request or nurse handoff"
    }
  },
  "if": {
    "properties": {
      "is_new_prescription": {
        "const": true
      }
    }
  },
  "then": {
    "properties": {
      "request_type": {
        "const": "nurse_escalation"
      }
    }
  }
}
```

**Nearest existing tool(s):** next_checkin, escalate_to_nurse

## What the backend needs
Two integrations required: (1) a mail-order pharmacy network API (e.g., Amazon Pharmacy, Nimble Rx, or an existing PBM partner) to place and track delivery orders; (2) a Non-Emergency Medical Transportation (NEMT) broker API (e.g., MTM, Modivcare, or Lyft Healthcare) to schedule and confirm rides. When request_type is nurse_escalation, the tool writes a pre-populated task to the existing escalate_to_nurse queue with medication names, is_new_prescription flag, and patient_note — no new backend needed for that path.

## Safety notes
1. Clinical firewall: the tool never advises on dosage, interactions, or prescription appropriateness — any clinical content in patient_note is passed verbatim to the nurse, not interpreted. 2. New-prescription hard-stop: if is_new_prescription is true the tool MUST set request_type to nurse_escalation regardless of what the caller supplied; the logistics order must not be created. 3. Consent: confirm patient consent to share address and medication list with third-party logistics vendors before dispatching. 4. Confirmation loop: send the patient an SMS confirmation with estimated delivery window or ride time so they can flag errors before a no-show. 5. Failure fallback: if the logistics API returns an error, fall through to escalate_to_nurse with the full context so no patient request is silently dropped.

## Decision
- [ ] Approve: `/expand tool-pharmacy_logistics`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
