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
| 37 | 23 | 1 | 59 |

## Outcomes, plan

| resolved | partial | failed | escalated |
|---|---|---|---|
| 9 | 31 | 0 | 0 |

## What patients raise, by tier

| urgent clinical | non-urgent clinical | non-clinical |
|---|---|---|
| 15 | 56 | 49 |

## Candidate expansions

| tool | persona | count | share | nearest existing | example |
|---|---|---|---|---|---|
| `lookup_member_by_name_or_phone` | plan | 39 | 97% | outcome_evidence, enrollment_status | enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found |
| `insurance_question` | patient | 20 | 17% | log_reading, next_checkin | any chance you can help with a prior auth? Insurance has been holding up my metoprolol refill for a week now. |
| `pharmacy_logistics` | patient | 19 | 16% | next_checkin, escalate_to_nurse | even once the script is sent, the nearest pharmacy is like 45 minutes out. Is there any way to set up mail delivery or get help with a ride? |
| `request_refill` | patient | 11 | 9% | log_reading, escalate_to_nurse | I've been out of lisinopril for three days. My truck's been in the shop and the pharmacy is 45 miles away. |
| `device_support` | patient | 8 | 7% | next_checkin, log_medication | Put the cuff on twice and it just says ERR both times. Dunno what's going on with it. |
| `diet_content` | patient | 7 | 6% | log_reading, next_checkin | my doctor keeps saying lay off the bread but I live 40 miles from the nearest grocery store. What am I supposed to eat instead? |
| `opt_out` | patient | 5 | 4% | log_reading, next_checkin | I just want off these texts. how do i stop them |
| `social_checkin` | patient | 5 | 4% | log_reading, log_medication | Nobody's made it out since the snow came. Two weeks now. |

Unanswered escalations: 344, from 342 patients.
