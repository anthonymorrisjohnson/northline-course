| # | expected | got | route | |
|---|---|---|---|---|
| 1 | non_urgent_clinical | non_urgent_clinical | nurse_routine |  |
| 2 | non_clinical | non_clinical | admin |  |
| 3 | non_clinical | non_clinical | admin |  |
| 4 | urgent_clinical | urgent_clinical | nurse_urgent |  |
| 5 | urgent_clinical | urgent_clinical | nurse_urgent | trap |
| 6 | non_urgent_clinical | non_urgent_clinical | nurse_routine |  |
| 7 | non_urgent_clinical | non_urgent_clinical | nurse_routine |  |
| 8 | non_clinical | non_clinical | admin |  |
| 9 | non_urgent_clinical | non_urgent_clinical | nurse_routine | trap |
| 10 | urgent_clinical | urgent_clinical | nurse_urgent |  |
| 11 | non_clinical | non_clinical | admin |  |
| 12 | urgent_clinical | urgent_clinical | nurse_urgent | trap |
| 13 | non_urgent_clinical | non_urgent_clinical | nurse_routine | trap |
| 14 | non_clinical | non_clinical | admin |  |
| 15 | non_clinical | non_clinical | admin |  |

Accuracy 100%. Urgent recall 1.0. Missed urgent: none. Non-clinical routed away from nurses: 100%.