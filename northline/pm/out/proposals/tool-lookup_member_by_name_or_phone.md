# Expansion proposal: `lookup_member_by_name_or_phone`

**Kind:** tool  **Persona(s):** patient, plan  **Evidence:** 39 conversations (97% of plan conversations)

## What users asked for
System cannot perform member lookup by name; pt-XXXX format required.

Example quotes:
- "enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found"
- "enrollment_status({"member_id": "Sandra Kowalski"}) -> not_found"
- "enrollment_status({"member_id": "312-555-0187"}) -> not_found"

## Proposed tool
**Docstring (what the model reads):** Resolve a caller's full name or phone number to their canonical pt-XXXX member ID so downstream tools (e.g. enrollment_status) can complete the request.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "full_name": {
      "type": "string",
      "description": "Patient's full legal name as enrolled (e.g. 'Sandra Okonkwo'). Provide this OR phone_number OR both."
    },
    "phone_number": {
      "type": "string",
      "description": "Patient's SMS or voice number in E.164 or local format (e.g. '312-555-0187')."
    },
    "patient_id": {
      "type": "string",
      "description": "Partial or candidate pt-XXXX ID if the caller supplied one; used to break ties when multiple records match name or phone.",
      "pattern": "^pt-[0-9]+$"
    }
  },
  "required": [],
  "minProperties": 1,
  "additionalProperties": false
}
```

**Nearest existing tool(s):** outcome_evidence, enrollment_status

## What the backend needs
Member directory search API (read-only) backed by the enrollment database. Must support case-insensitive, fuzzy full-name matching and exact phone-number lookup; returns the canonical pt-XXXX member ID plus enrollment status. No clinical records are accessed or returned. When multiple candidates match, the API must return a "ambiguous" signal rather than a list of records, so the agent can escalate to a nurse with the collected identifiers as context.

## Safety notes
1. Minimum-disclosure: return only the pt-XXXX member ID and enrollment status — no DOB, address, diagnoses, or clinical data. 2. Tie-breaking policy: if more than one member matches, do not return any record; instead hand off to the nurse queue with {full_name, phone_number, patient_id} so a human can verify identity. 3. Enumeration guard: rate-limit to 3 failed lookups per SMS session before locking and routing to nurse. 4. Audit log: every call must record the queried identifiers, the agent session ID, and the result code for HIPAA access-log compliance. 5. No clinical routing: this tool is strictly administrative identity resolution; any clinical question that surfaces during the lookup (e.g. "my medication wasn't refilled") must be passed, with member context, to the nurse queue — the tool must never surface clinical guidance itself.

## Decision
- [ ] Approve: `/expand tool-lookup_member_by_name_or_phone`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
