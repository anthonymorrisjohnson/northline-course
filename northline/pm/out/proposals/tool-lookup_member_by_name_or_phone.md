# Expansion proposal: `lookup_member_by_name_or_phone`

**Kind:** tool  **Persona(s):** SMS check-in agent (primary caller — needs a valid pt-XXXX before calling enrollment_status or outcome_evidence), Nurse coordinator (receives disambiguation queue when match confidence is ambiguous), Enrollment/ops team (audits lookup logs for access-compliance review)  **Evidence:** 39 conversations (97% of plan conversations)

## What users asked for
System cannot perform member lookup by name; pt-XXXX format required.

Example quotes:
- "enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found"
- "enrollment_status({"member_id": "Sandra Kowalski"}) -> not_found"
- "enrollment_status({"member_id": "312-555-0187"}) -> not_found"

## Proposed tool
**Docstring (what the model reads):** Resolve a patient's pt-XXXX member ID from a full name or phone number so downstream tools (e.g. enrollment_status) can be called with a valid identifier.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "patient_id": {
      "type": "string",
      "description": "Already-known pt-XXXX identifier; if provided, lookup is skipped and the value is returned directly."
    },
    "full_name": {
      "type": "string",
      "description": "Patient's full legal name (first last). Used for fuzzy match if patient_id is absent."
    },
    "phone_number": {
      "type": "string",
      "description": "Patient's phone number in E.164 or local format. Used for exact match if patient_id is absent."
    }
  },
  "required": [],
  "additionalProperties": false
}
```

**Nearest existing tool(s):** outcome_evidence, enrollment_status

## What the backend needs
Member directory / EHR identity service — read-only query against the member registry that maps (name, phone) → pt-XXXX; must support fuzzy name matching (e.g. Soundex or trigram) to handle common misspellings; returns at most one confirmed match or a ranked list of candidates for human disambiguation; no PHI written.

## Safety notes
1. Returns only the member ID (pt-XXXX) and enrollment status — no clinical data, vitals, or care-plan details in the response payload. 2. If the name query returns 2+ candidates with similarity score within 0.15 of each other, the tool must NOT auto-select; it must surface candidates to a nurse queue for manual confirmation before any downstream tool is invoked. 3. Phone lookup is exact-match only — no fuzzy fallback — to prevent cross-patient ID confusion. 4. All lookup attempts are audit-logged with the querying session ID, timestamp, and input type (name vs. phone) for HIPAA access-log compliance. 5. This tool does not deliver, interpret, or route clinical information; it is an identity-resolution step only. Any subsequent clinical action (medication question, symptom triage, etc.) must go through the nurse escalation path, not through this tool's response.

## Decision
- [ ] Approve: `/expand tool-lookup_member_by_name_or_phone`
- [ ] Reject, reason:
- [ ] Merge into existing tool:
