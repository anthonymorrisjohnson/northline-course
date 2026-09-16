# Northline PM loop report

160 conversations and sessions classified; 155 escalations a week in the queue log.

## The board's numbers next to the logs

| metric | Board deck | From logs |
|---|---|---|
| Escalations per week | 2400.0 | 155 |
| Median nurse response (h) | 29.72 | 28.9 (p90 69.7) |
| Urgent escalations, median response (h) | not reported | 27.4 |
| After-hours share | 0.46 | 0.47 |
| Non-clinical share of the nurse queue | not reported | 0.39 |
| Patients inactive after an escalation | 334 | 219 |

## Outcomes, patient

| resolved | partial | failed | escalated |
|---|---|---|---|
| 38 | 24 | 1 | 57 |

## Outcomes, plan

| resolved | partial | failed | escalated |
|---|---|---|---|
| 17 | 23 | 0 | 0 |

## What patients raise, by tier

| urgent clinical | non-urgent clinical | non-clinical |
|---|---|---|
| 18 | 51 | 51 |

## Candidate expansions

| tool | persona | count | share | nearest existing | example |
|---|---|---|---|---|---|
| `insurance_question` | patient | 21 | 17% | log_reading, next_checkin | Any chance you can help with a prior auth? Insurance has been holding up my metoprolol refill for a week now. |
| `lookup_member_by_name` | plan | 21 | 53% | member_engagement, outcome_evidence | enrollment_status({"member_id": "Margaret Osei"}) -> not_found |
| `pharmacy_logistics` | patient | 17 | 14% | log_reading, escalate_to_nurse | Any way to set up a delivery or get a ride covered through this program? |
| `lookup_member_by_phone` | plan | 10 | 25% | outcome_evidence, enrollment_status | enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found |
| `device_support` | patient | 8 | 7% | next_checkin, log_medication | Put the cuff on twice and it just says ERR both times. Dunno what's going on with it. |
| `lookup_member_by_display_name` | plan | 8 | 20% | member_engagement, outcome_evidence | enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found |
| `request_refill` | patient | 8 | 7% | log_reading, escalate_to_nurse | While I'm waiting can you at least send in a refill on my lisinopril? I'm running low. |
| `diet_content` | patient | 7 | 6% | log_reading, next_checkin | my doctor keeps saying lay off the bread but I live 40 miles from the nearest grocery store. What am I supposed to eat instead? |
| `opt_out` | patient | 5 | 4% | log_reading, log_medication | I just want off these texts. how do i stop them |
| `social_checkin` | patient | 4 | 3% | log_reading, log_medication | Nobody's made it out since the snow came. Two weeks now. |
| `emergency_transport` | patient | 1 | 1% | log_reading, log_medication | Is there any way you can help me get a ride out there? I'm 40 miles from the clinic and don't have anyone who can drive me today. |
| `transportation_support` | patient | 1 | 1% | log_reading, escalate_to_nurse | any chance you can help me get a ride to my clinic? It's 45 minutes away and I don't have a car. |

Unanswered escalations: 238, from 219 patients.
