# Ablation: reference agent with one check switched off

| Check switched off | Cases passed | Cases with a critical error | Gate | Cases that caught it |
|---|---|---|---|---|
| merge | 23 of 25 | 2 | FAIL | 8, 20 |
| po_match | 24 of 25 | 1 | FAIL | 15 |
| handoff | 15 of 25 | 10 | FAIL | 16, 17, 18, 19, 20, 21, 22, 23, 24, 25 |
| fcfs | 24 of 25 | 0 | pass | 3 |
| dedupe | 24 of 25 | 1 | FAIL | 5 |
| calendar | 24 of 25 | 1 | FAIL | 10 |
| notice | 24 of 25 | 1 | FAIL | 12 |
| timezone | 22 of 25 | 3 | FAIL | 9, 11, 18 |
| transit | 21 of 25 | 4 | FAIL | 6, 9, 11, 18 |
| window | 23 of 25 | 2 | FAIL | 16, 20 |
| reply | 24 of 25 | 1 | FAIL | 14 |
| fallback | 24 of 25 | 0 | pass | 13 |
