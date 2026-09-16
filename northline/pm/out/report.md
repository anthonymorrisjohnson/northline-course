# Northline PM loop report

160 conversations and sessions classified; 2401 escalations a week in the queue log.

## The board's numbers next to the logs

| metric | Board deck | From logs |
|---|---|---|
| Escalations per week | 2400 | 2401 |
| Median nurse response (h) | 31 | 29.6 (p90 72.9) |
| Urgent escalations, median response (h) | not reported | 29.1 |
| After-hours share | 0.46 | 0.46 |
| Non-clinical share of the nurse queue | not reported | 0.4 |
| Patients inactive after an escalation | 340 | 342 |

## Outcomes, patient

| resolved | partial | failed | escalated |
|---|---|---|---|
| 40 | 19 | 4 | 57 |

## Outcomes, plan

| resolved | partial | failed | escalated |
|---|---|---|---|
| 20 | 20 | 0 | 0 |

## What patients raise, by tier

| urgent clinical | non-urgent clinical | non-clinical |
|---|---|---|
| 14 | 78 | 28 |

## Candidate expansions

| tool | persona | count | share | nearest existing | example |
|---|---|---|---|---|---|
| `lookup_member_by_name_or_phone` | plan | 39 | 97% | outcome_evidence, enrollment_status | enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found |
| `insurance_question` | patient | 21 | 17% | log_reading, next_checkin | Any chance you can help with a prior auth? Insurance has been holding up my metoprolol refill for a week now. |
| `pharmacy_logistics` | patient | 16 | 13% | log_medication, escalate_to_nurse | I've been out of lisinopril for three days. My truck's been in the shop and the pharmacy is 45 miles away. |
| `request_refill` | patient | 14 | 12% | log_reading, escalate_to_nurse | Yeah, I'm almost out of my lisinopril and my insurance has been rejecting the refill for two weeks. |
| `device_support` | patient | 7 | 6% | next_checkin, log_medication | Put the cuff on twice and it just says ERR both times. Dunno what's going on with it. |
| `diet_content` | patient | 7 | 6% | log_reading, next_checkin | my doctor keeps saying lay off the bread but I live 40 miles from the nearest grocery store. What am I supposed to eat instead? |
| `opt_out` | patient | 5 | 4% | log_reading, next_checkin | I just want off these texts. how do i stop them |
| `social_checkin` | patient | 4 | 3% | log_reading, log_medication | I think I just wanted somebody to check in. Silly maybe. |

Unanswered escalations: 344, from 342 patients.
