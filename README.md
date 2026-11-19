# Appointment agent eval

A runnable version of the 25-case eval set in my appointment agent spec for Runbook, which describes an agent that books and reschedules pickup and delivery appointments for a freight brokerage (Integrity Express Logistics) and the gate it must pass before it writes to the TMS without a coordinator's review. The harness scores an agent on each case, runs every case three times, and applies the same gate as the spec.

All data here is constructed test data. The TMS and the facility calendars are mocks (15 facilities across three time zones, 27 loads, dock hours, holidays, notice rules, booking channels, and booked slots). Nothing comes from Integrity's or Runbook's systems.

**Demo page:** https://pg2342-hub.github.io/appointment-agent-eval/ lets you switch any of the 12 checks off and see which cases catch it and whether the gate still passes. It shows precomputed results for all 4,096 combinations, produced by `python3 docs/build_page.py` with the same grader.

## Run it

```
python3 run_eval.py --agent spec            # reference agent
python3 run_eval.py --agent naive           # the same agent with every check switched off
python3 ablation.py                         # switch off one check at a time
python3 -m unittest discover -s tests -t .  # 8 tests
```

Python 3.9+ and the standard library only. Reports go to `reports/`.

To score your own agent, write a class with `propose(case, tms)` that returns a proposal (below) and run `python3 run_eval.py --agent my_module:MyAgent`. A live-model agent would read the request and a snapshot of the TMS and return the same shape. Each case runs three times because a model's answers vary between runs, and a case passes only if it passes every run.

## What is in it

| Path | What it is |
|---|---|
| `data/tms_mock.json` | The mock TMS: facilities (time zone, dock hours, holidays, notice hours, booking channel, first-come first-served or not, booked slots), loads (load number, customer PO, pickup and delivery stops, customer window, miles, carrier, hazmat), and the transit rule (50 mph plus one hour at the dock). |
| `data/cases.json` | The 25 cases from the spec's eval page: the request facts, any reply from the facility, and the expected outcome. T1 clean (7), T2 messy but in scope (8), T3 needs judgment, hand off (6), T4 out of scope (4). |
| `harness/agents.py` | `SpecAgent`, a reference implementation of the spec with 12 checks that can be switched off, and `NaiveAgent`, which has all of them off and books whatever it can. |
| `harness/grader.py` | Grades one proposal and returns error codes E1 to E6 from the spec. E3 (wrong appointment written, including a duplicate booking or a booking on the wrong load) and E4 (should have handed off) are critical. |
| `run_eval.py` | Runs an agent over the cases and applies the gate. |
| `ablation.py` | Runs the reference agent with one check switched off at a time. |
| `docs/` | The demo page (`index.html`) and `build_page.py`, which writes `results.js`. |

The gate: 24 of 25 cases on all three runs, zero critical errors, T1-T2 at 14 of 15 or better, and T3-T4 at 10 of 10.

A proposal is one of: `book` (load, appointments as facility and local time, channel, attempts, the confirmation number the facility returned (`tms.confirmation`), who was notified, flags for the account executive), `enter_existing` (an appointment the customer already booked), `record_fcfs` (no appointment needed), or `handoff` (to the coordinator or the account executive, with a reason and a log line).

## Results

| Agent | Cases passed | T1-T2 | T3-T4 | Cases with a critical error | Gate |
|---|---|---|---|---|---|
| Reference (`spec`) | 25 of 25 | 15 of 15 | 10 of 10 | 0 | Pass |
| All checks off (`naive`) | 4 of 25 | 4 of 15 | 0 of 10 | 19 | Fail |

How to read these. The reference agent reads structured facts, not raw email, so its 25 of 25 shows that the spec's rules can be written as code and that the grader agrees with a correct policy. It is not a claim about a model. The naive agent shows what the grader catches when an agent books whatever it can: appointments the receiver cannot meet, bookings on a holiday, a second booking on top of the customer's, and every case that should have gone to a person.

## Ablation

An eval set that still passes with a check switched off is not testing that check.

| Check switched off | Cases passed | Cases with a critical error | Gate | Cases that caught it |
|---|---|---|---|---|
| Merge facts split across emails | 23 of 25 | 2 | Fail | 8, 20 |
| Match PO and facility together | 24 of 25 | 1 | Fail | 15 |
| Hand-off rule | 15 of 25 | 10 | Fail | 16 to 25 |
| First-come, first-served receivers | 24 of 25 | 0 | **Pass** | 3 |
| Do not book on top of a customer booking | 24 of 25 | 1 | Fail | 5 |
| Facility days and holidays | 24 of 25 | 1 | Fail | 10 |
| Notice rules | 24 of 25 | 1 | Fail | 12 |
| Time zones | 22 of 25 | 3 | Fail | 9, 11, 18 |
| Transit time and carrier ETA | 21 of 25 | 4 | Fail | 6, 9, 11, 18 |
| Customer window | 23 of 25 | 2 | Fail | 16, 20 |
| Read the facility's counter-offer | 24 of 25 | 1 | Fail | 14 |
| Portal retry and email fallback | 24 of 25 | 0 | **Pass** | 13 |

What this says about the eval set. Seven of the twelve checks (PO and facility matching, first-come first-served receivers, customer bookings, holidays, notice rules, counter-offers, and the portal fallback) are each caught by a single case, which is the thinnest coverage and the first place to add cases built from a broker's own loads. Two checks can be switched off and the gate still passes. With the portal fallback off, the agent hands the request to a coordinator, which is a safe, low-severity miss and exactly what the one allowed miss is for. With the first-come, first-served check off, the agent books an appointment the receiver does not need, which is wasted work rather than a wrong write. Neither is critical, but a second case for each would stop either from slipping through.

## Limits

- The cases are written by hand, and the expected outcomes encode one reading of the spec. A real version would be built from a broker's own appointment emails and reviewed with its coordinators.
- The grader checks outcomes (load, facility, time, channel, notifications, flags, hand-offs). It does not grade the wording of emails to facilities or carriers.
- Transit is a flat 50 mph plus one hour at the dock, with no hours-of-service breaks. A real version would use the carrier's own ETA wherever there is one.
- 25 cases is a go-live gate for one broker, not a benchmark. The shadow stage in the spec covers what the cases cannot.
