# Expansion proposal: `lookup_member_by_name_or_phone`

**Kind:** tool  **Persona(s):** SMS check-in agent (primary caller), nurse (receives handoff on rate-limit or disambiguation failure)  **Evidence:** 39 conversations (97% of plan conversations)

## What users asked for
Cannot look up member enrollment by name; system requires pt-XXXX format member ID.

Example quotes:
- "enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found"
- "enrollment_status({"member_id": "Sandra Kowalski"}) -> not_found"
- "enrollment_status({"member_id": "312-555-0187"}) -> not_found"

## Proposed tool
**Docstring (what the model reads):** Resolves a patient's canonical pt-XXXX member ID from a full or partial name and/or phone number so downstream tools (e.g. enrollment_status) can operate on a confirmed identity.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "pt-XXXX ID if already partially known; used to validate or narrow the match."
    },
    "full_name": {
      "type": "string",
      "description": "Patient full name as entered or spoken. Case-insensitive, diacritic-tolerant fuzzy match."
    },
    "phone_number": {
      "type": "string",
      "description": "10-digit US phone number, any formatting accepted (e.g. 312-555-0187)."
    }
  },
  "required": [],
  "minProperties": 1,
  "additionalProperties": false
}
```

**Nearest existing tool(s):** outcome_evidence, enrollment_status

## What the backend needs
Patient enrollment directory (read-only): fuzzy-name index + phone → pt-XXXX mapping table. Must be backed by the same source of truth as enrollment_status. Requires: HIPAA-compliant audit logging per lookup, no write access.

## Safety notes
1. Returns only pt-XXXX member ID and an enrollment-status flag — no PHI, clinical history, or contact details. 2. If zero matches: return not_found with a prompt for the agent to ask the patient to confirm spelling or try their phone number — never guess. 3. If multiple matches (name collision): return match_count only and ask the patient for their phone number or date of birth to disambiguate; never enumerate names to the patient. 4. All lookups are audit-logged (caller, inputs, timestamp, match result) for HIPAA compliance. 5. Rate-limit per session: 5 attempts before routing the conversation to a nurse with full context (name/phone tried, match count) so a human can verify identity safely.

## Decision
- [ ] Approve: `/expand tool-lookup_member_by_name_or_phone`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
