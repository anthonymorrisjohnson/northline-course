# Expansion proposal: `lookup_member_by_name_or_phone`

**Kind:** tool  **Persona(s):** patient, plan  **Evidence:** 39 conversations (97% of plan conversations)

## What users asked for
Tool requires member ID in pt-XXXX format but staff attempted name-based lookup.

Example quotes:
- "enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found"
- "enrollment_status({"member_id": "Sandra Kowalski"}) -> not_found"
- "enrollment_status({"member_id": "312-555-0187"}) -> not_found"

## Proposed tool
**Docstring (what the model reads):** Resolve a member's canonical `pt-XXXX` ID from a full name or phone number so downstream tools (e.g., `enrollment_status`) can be called with a valid identifier.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "full_name": {
      "type": "string",
      "description": "Patient's full legal name as it appears on enrollment records (e.g., 'Sandra Okonkwo')."
    },
    "phone_number": {
      "type": "string",
      "description": "Patient's registered phone number in E.164 or local format (e.g., '312-555-0187')."
    },
    "patient_id": {
      "type": "string",
      "description": "Partial or approximate pt-XXXX member ID if the caller has one but is unsure of formatting.",
      "pattern": "^pt-[0-9]{4}$"
    }
  },
  "anyOf": [
    {
      "required": [
        "full_name"
      ]
    },
    {
      "required": [
        "phone_number"
      ]
    },
    {
      "required": [
        "patient_id"
      ]
    }
  ],
  "additionalProperties": false
}
```

**Nearest existing tool(s):** outcome_evidence, enrollment_status

## What the backend needs
Member identity-resolution service (read-only query against the enrollment directory). Must support fuzzy-match on `full_name` (Levenshtein ≤ 2 to guard against misspellings) and exact-match on normalized `phone_number`. Returns the canonical `pt-XXXX` member ID plus a confidence score; callers must pass the result to `enrollment_status` for full record access. No PHI beyond the matched ID is returned by this tool itself.

## Safety notes
1. **Identity confirmation before action**: a fuzzy-name match with confidence < 1.0 must prompt the agent to verbally confirm at least one additional identifier (DOB or phone) with the patient before the returned ID is used in any downstream call. 2. **No clinical data surfaced**: this tool returns only the member ID — never diagnosis, medication, or care-plan data; clinical questions must be routed to a nurse via `escalate_to_nurse` with the resolved ID as context. 3. **PII minimization**: phone numbers and names are logged only as hashed tokens in the audit trail. 4. **Rate limiting**: max 5 lookups per session to deter enumeration attacks against the member directory. 5. **Ambiguous match handling**: if two or more records match with equal confidence, the tool returns `ambiguous_match` and must hand off to a human staff member rather than guessing.

## Decision
- [ ] Approve: `/northline-expand tool-lookup_member_by_name_or_phone`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
