# Eval report: `spec` agent

25 of 25 cases passed on all 3 runs. T1-T2 15 of 15, T3-T4 10 of 10, cases with a critical error 0. Gate (24 of 25 cases on all three runs, zero critical errors, T1-T2 at 14 of 15 or better, T3-T4 at 10 of 10): **PASS**.

| # | Tier | Case | Result | Errors |
|---|---|---|---|---|
| 1 | T1 | New delivery appointment; facility books by email; customer window open; all references present | pass |  |
| 2 | T1 | New pickup appointment at a facility with a web scheduling portal | pass |  |
| 3 | T1 | Delivery to a first-come, first-served receiver | pass |  |
| 4 | T1 | Phone-only facility, called during business hours | pass |  |
| 5 | T1 | Customer email already contains a booked appointment | pass |  |
| 6 | T1 | Pickup and delivery both need appointments, 300 miles apart | pass |  |
| 7 | T1 | Carrier already assigned when the appointment is confirmed | pass |  |
| 8 | T2 | Request split across two emails; PO number only in the second | pass |  |
| 9 | T2 | Central-time pickup, Eastern-time delivery | pass |  |
| 10 | T2 | Requested delivery date is a facility holiday closure | pass |  |
| 11 | T2 | Check call shows the carrier running 3 hours late | pass |  |
| 12 | T2 | Facility requires 48 hours notice; request arrives same day | pass |  |
| 13 | T2 | Portal returns an error on booking | pass |  |
| 14 | T2 | Facility counter-offers a different slot inside the window | pass |  |
| 15 | T2 | Request uses the customer's PO; TMS stores the load by Integrity's load number | pass |  |
| 16 | T3 | Only slots available fall outside the customer window | pass |  |
| 17 | T3 | Delivery date in the customer email conflicts with the TMS | pass |  |
| 18 | T3 | A reschedule would make the load late to the final receiver | pass |  |
| 19 | T3 | Facility asks for a driver-assist or lumper detail not in the load record | pass |  |
| 20 | T3 | Two Integrity loads at the same facility, one dock slot left | pass |  |
| 21 | T3 | Receiver says the PO is not in its system | pass |  |
| 22 | T4 | Customer complains about a missed appointment and a detention charge | pass |  |
| 23 | T4 | Carrier asks about rate or an accessorial charge | pass |  |
| 24 | T4 | Customer asks to change the delivery address | pass |  |
| 25 | T4 | Hazmat load with special facility instructions | pass |  |
