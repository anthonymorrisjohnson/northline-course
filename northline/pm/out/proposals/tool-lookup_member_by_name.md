# Expansion proposal: `lookup_member_by_name`

**Kind:** tool  **Persona(s):** SMS check-in agent (primary caller — resolves name before calling member_engagement or outcome_evidence), Care coordinator / nurse (receives routed context on ambiguous or no-match cases), Enrollment ops (audits lookup logs for data-quality issues driving name mismatches)  **Evidence:** 21 conversations (53% of plan conversations)

## What users asked for
Member lookup by name not supported; system requires pt-XXXX format instead.

Example quotes:
- "enrollment_status({"member_id": "Margaret Osei"}) -> not_found"
- "enrollment_status({"member_id": "Judith Walcott"}) -> not_found"
- "enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found"

## Proposed tool
**Docstring (what the model reads):** Resolve a patient's full name to their Northline member ID (pt-XXXX format) so the agent can proceed with any downstream tool that requires a structured member_id.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "full_name": {
      "type": "string",
      "description": "Patient's full name as provided (e.g. 'Margaret Osei'). Case-insensitive, partial matches allowed."
    },
    "date_of_birth": {
      "type": "string",
      "format": "date",
      "description": "ISO 8601 date (YYYY-MM-DD). Required when name alone returns >1 match to disambiguate without exposing other members' records."
    },
    "patient_id": {
      "type": "string",
      "description": "If the caller already has a pt-XXXX ID, pass it here to skip name resolution and return enriched identity context directly."
    }
  },
  "required": [
    "full_name"
  ],
  "additionalProperties": false
}
```

**Nearest existing tool(s):** member_engagement, outcome_evidence

## What the backend needs
Member identity/enrollment database — read-only SELECT on the members table against (normalized_last_name, normalized_first_name, dob) with a fuzzy-match fallback (trigram or Soundex). Must return exactly one canonical member_id or a structured disambiguation response; never a raw list of all matches. No write path.

## Safety notes
1. **PHI minimization**: return only member_id + display_name on a single hit; never surface DOB, address, or clinical fields in the tool response. 2. **Ambiguous match → nurse routing**: if 2+ members match the name (and no DOB was supplied or DOB also matches multiple), return a `requires_verification` flag and route the conversation to a nurse with the candidate member_ids — do not present the list to the patient. 3. **No-match handling**: a not_found result is administrative, not clinical; the agent should ask the patient to confirm spelling or supply DOB — never infer clinical meaning from the absence of a record. 4. **Audit log**: every call must be logged with the agent session ID and the queried name so identity-resolution attempts are auditable for HIPAA compliance. 5. **This tool is not a clinical pathway**: it resolves identity only; any health question that surfaces during lookup must be routed to a nurse with the resolved context (or unresolved context if lookup fails), not answered by the agent.

## Decision
- [ ] Approve: `/expand tool-lookup_member_by_name`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
