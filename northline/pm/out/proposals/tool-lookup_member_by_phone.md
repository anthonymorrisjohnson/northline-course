# Expansion proposal: `lookup_member_by_phone`

**Kind:** tool  **Persona(s):** SMS check-in agent (automated caller), care coordinator performing manual outreach, enrollment team resolving registration gaps  **Evidence:** 10 conversations (25% of plan conversations)

## What users asked for
Member lookup by name not supported; system requires pt-XXXX patient ID format.

Example quotes:
- "enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found"
- "enrollment_status({"member_id": "Sandra Kowalski"}) -> not_found"
- "enrollment_status({"member_id": "312-555-0187"}) -> not_found"

## Proposed tool
**Docstring (what the model reads):** Given a patient's phone number as captured from the inbound SMS channel, resolve and return their canonical patient_id (pt-XXXX format) so downstream tools such as enrollment_status can be called without requiring the patient to know their ID.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "phone_number": {
      "type": "string",
      "description": "E.164-formatted phone number of the inbound SMS sender (e.g. +13125550187). Must be the verified originating number from the SMS gateway \u2014 never user-supplied text.",
      "pattern": "^\\+1[2-9]\\d{9}$"
    },
    "patient_id": {
      "type": "string",
      "description": "Optional: pt-XXXX ID if already known; when provided the tool validates the phone matches and returns the same ID, skipping registry lookup.",
      "pattern": "^pt-\\d{4,}$"
    }
  },
  "required": [
    "phone_number"
  ],
  "additionalProperties": false
}
```

**Nearest existing tool(s):** outcome_evidence, enrollment_status

## What the backend needs
Member registry service (EHR or CRM) with a phone-to-patient-ID index. Must support exact-match lookup on verified E.164 numbers and return only the patient's own record. Requires read-only HIPAA-compliant access; all queries must be audit-logged with the inbound session ID. If zero or multiple records match, the service must return an explicit ambiguous/not_found status rather than a best-guess record.

## Safety notes
1. Phone number MUST come from the verified SMS gateway sender field — never accept it as free text typed by the patient, to prevent one patient looking up another's ID. 2. Return only patient_id; strip all other PHI (name, DOB, address) from the response payload so the agent never holds more data than it needs. 3. On not_found or ambiguous result, do NOT surface clinical status guesses; instead enqueue a nurse callback with the originating phone number, session transcript, and a "identity unresolved" flag so a care coordinator can manually verify and link the account. 4. Rate-limit to 3 attempts per phone number per hour and lock the channel on repeated failures to prevent enumeration attacks. 5. This tool is administrative only — it resolves identity, nothing clinical. Any subsequent clinical question must still be routed to a nurse via the standard triage path.

## Decision
- [ ] Approve: `/expand tool-lookup_member_by_phone`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
