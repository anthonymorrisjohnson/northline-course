# Northline PM loop report

160 conversations and sessions classified; 2401 escalations a week in the queue log.

## The board's numbers next to the logs

| metric | Board deck | From logs |
|---|---|---|
| Escalations per week | 2400 | 2401 |
| Median nurse response (h) | 29.72 | 29.6 (p90 72.9) |
| Urgent escalations, median response (h) | not reported | 29.1 |
| After-hours share | 0.46 | 0.46 |
| Non-clinical share of the nurse queue | not reported | 0.4 |
| Patients inactive after an escalation | 334 | 342 |

## Outcomes, patient

| resolved | partial | failed | escalated |
|---|---|---|---|
| 37 | 25 | 2 | 56 |

## Outcomes, plan

| resolved | partial | failed | escalated |
|---|---|---|---|
| 1 | 39 | 0 | 0 |

## What patients raise, by tier

| urgent clinical | non-urgent clinical | non-clinical |
|---|---|---|
| 15 | 50 | 54 |

## Candidate expansions

| tool | persona | count | share | nearest existing | example |
|---|---|---|---|---|---|
| `lookup_member_by_name_or_phone` | plan | 39 | 97% | outcome_evidence, enrollment_status | enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found |
| `insurance_question` | patient | 19 | 16% | log_reading, next_checkin | any chance you can help with a prior auth? Insurance has been holding up my metoprolol refill for a week now. |
| `pharmacy_logistics` | patient | 19 | 16% | escalate_to_nurse, log_reading | That's the problem. I've been out of lisinopril for three days. My truck's been in the shop and the pharmacy is 45 miles away. |
| `request_refill` | patient | 12 | 10% | log_reading, escalate_to_nurse | While I'm waiting can you at least send in a refill on my lisinopril? I'm running low. |
| `device_support` | patient | 7 | 6% | next_checkin, log_medication | Put the cuff on twice and it just says ERR both times. Dunno what's going on with it. |
| `diet_content` | patient | 6 | 5% | log_reading, next_checkin | Saw something about cutting white bread but I don't know what to eat instead. Any ideas? |
| `opt_out` | patient | 5 | 4% | log_reading, log_medication | I just want off these texts. how do i stop them |
| `social_checkin` | patient | 5 | 4% | log_reading, log_medication | Nobody's made it out since the snow came. Two weeks now. |

Unanswered escalations: 344, from 342 patients.
