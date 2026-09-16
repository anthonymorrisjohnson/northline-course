# Northline conversation taxonomy

Classify each check-in conversation or plan tool-log session into one record.

- **intent**: what the user wanted, five words or fewer. Examples: weekly reading, refill request, insurance denial, diet question, device error, social contact, opt out, pull outcome evidence.
- **tier**: for patient conversations, the clinical tier of what they raised: `urgent_clinical` (chest pain, possible stroke, glucose under 70 or over 300, BP at or above 180/110, double dose with symptoms), `non_urgent_clinical` (routine readings, mild symptoms, stopped a medication, a wound, diet, refills), `non_clinical` (insurance, scheduling, logistics, device support, social contact, opt-out). Plan sessions are `none`.
  A weekly check-in that only logs a reading, even one flagged high and escalated, is `non_urgent_clinical`, not `non_clinical`.
- **outcome**: `resolved`, `partial`, `failed` (nothing useful and no handoff), `escalated` (handed to a nurse).
- **tools_used**: tool names that appear.
- **unmet_need**: true when the user asked for something no available tool could do, even if the assistant declined gracefully. A polite "I can't do that yet" is still an unmet need.
- **unmet_need_description**: one sentence.
- **proposed_tool**: snake_case, reused across conversations for the same need: `request_refill`, `insurance_question`, `pharmacy_logistics`, `diet_content`, `device_support`, `social_checkin`, `opt_out`, `lookup_member_by_name_or_phone`, `bulk_outcome_export`. Empty when none.
- **evidence_quote**: the single user line that best shows the need, verbatim.

Rules: a clinical question (a symptom, a reading, a medication worry) that was escalated is `escalated` and not an unmet need. A request the agent could not perform (a refill, an insurance question, transport, a device problem) is an unmet need with a proposed tool even when the agent passed it to a nurse. Never propose a tool that would give clinical advice; if a patient wanted advice, set unmet_need true and proposed_tool empty so the count shows the demand without a tool.
