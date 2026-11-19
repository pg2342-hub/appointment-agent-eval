"""Reference agent for the appointment spec, and the same agent with checks switched off.

An agent is any object with propose(case, tms) -> dict. The proposal shape is documented
in README.md. These agents read the structured facts in each case, not raw email text.
"""
from datetime import datetime, timedelta

CHECKS = [
    "merge",      # merge facts split across several emails
    "po_match",   # match the customer PO together with the facility, not the PO alone
    "handoff",    # the hand-off rule (out of scope, hazmat, conflicts, no slot, late, questions)
    "fcfs",       # recognise first-come, first-served receivers
    "dedupe",     # enter an appointment the customer already booked instead of booking again
    "calendar",   # facility days, weekends, and holidays
    "notice",     # facility notice rules
    "timezone",   # convert between facility time zones
    "transit",    # earliest arrival from pickup time + transit, or from the carrier's ETA
    "window",     # stay inside the customer window
    "reply",      # read the facility's reply (counter-offers)
    "fallback",   # retry a failed portal once, then fall back to email
]


class SpecAgent:
    name = "spec"

    def __init__(self, off=()):
        self.off = set(off)

    def on(self, check):
        return check not in self.off

    def propose(self, case, tms):
        req = case["request"]
        fresp = case.get("facility_response", {})
        received = datetime.fromisoformat(req["received_at"])
        emails = req["emails"]

        # 1. Gather facts. Several POs mean several loads; otherwise later emails fill gaps.
        facts = dict(emails[0])
        if self.on("merge"):
            for e in emails[1:]:
                for k, v in e.items():
                    facts.setdefault(k, v)
        pos = [e["po"] for e in (emails if self.on("merge") else emails[:1]) if "po" in e]
        pos = list(dict.fromkeys(pos))
        fac = facts.get("facility")

        loads = []
        for po in pos:
            cands = tms.find_by_po(po)
            if self.on("po_match") and fac:
                cands = [l for l in cands if fac in (l["delivery"]["facility"], l["pickup"]["facility"])]
            if cands:
                loads.append(cands[0])
        if not loads and fac and not self.on("merge"):
            # without merged facts the agent guesses: first open load at that facility
            l = tms.first_open_load_at(fac)
            if l:
                loads = [l]
        if not loads:
            # spec: ask the account executive once, then hand off; never guess the load
            return self._handoff("ae", "load_not_found", None, "No load in the TMS matches the PO and facility.")
        load = loads[0]
        ln = load["load_no"]

        # 2. Hand-off rule, before anything is booked.
        if self.on("handoff"):
            intent = req.get("intent", "appointment")
            if intent == "address_change":
                return self._handoff("ae", "changes_load", ln, "Address change alters the load; AE owns it.")
            if intent != "appointment":
                return self._handoff("coordinator", "out_of_scope", ln, f"Not an appointment request ({intent}).")
            if load["hazmat"]:
                return self._handoff("coordinator", "hazmat", ln, "Hazmat load needs special facility instructions.")
            if "requested_date" in facts:
                ws, we = load["delivery"]["window_start"][:10], load["delivery"]["window_end"][:10]
                if not (ws <= facts["requested_date"] <= we):
                    return self._handoff("ae", "date_conflict", ln,
                                         f"Email asks for {facts['requested_date']}, TMS window is {ws} to {we}.")
            if fresp.get("po_not_found"):
                return self._handoff("ae", "po_not_found", ln, "Receiver says the PO is not in its system.")
            if fresp.get("question"):
                return self._handoff("coordinator", "facility_question", ln,
                                     f"Facility asked: {fresp['question']} Not in the load record.")

        stop = req.get("stop", "delivery")
        dfac = load["delivery"]["facility"]

        # 3. First-come, first-served receivers need no appointment.
        if stop == "delivery" and self.on("fcfs") and tms.facilities[dfac]["fcfs"]:
            f = tms.facilities[dfac]
            return dict(action="record_fcfs", load=ln, facility=dfac,
                        notify=["carrier"] if load["carrier_assigned"] else [],
                        log=f"{dfac} receives first come, first served {f['open']}-{f['close']}; no appointment needed.")

        # 4. Customer already booked it: verify and enter, do not book again.
        if self.on("dedupe") and facts.get("existing_appt"):
            return dict(action="enter_existing", load=ln, confirmation=facts.get("confirmation"),
                        appointments=[dict(facility=dfac, local=facts["existing_appt"])], notify=[],
                        log="Customer-booked appointment entered; no new booking made.")

        appts, flags, notify = [], set(), set()
        pickup_dt = None
        if stop in ("pickup", "both"):
            p = load["pickup"]
            slot, why = self._pick(tms, p["facility"], p["window_start"], p["window_end"], received, None, flags)
            if slot is None:
                return self._handoff("coordinator", "no_slot_in_window", ln, why)
            appts.append(dict(facility=p["facility"], local=tms.fmt(p["facility"], slot)))
            pickup_dt = slot
            if stop == "pickup":
                return self._book(tms, case, load, appts, p["facility"], flags, notify)

        # 5. Delivery: earliest arrival from the carrier's ETA, or pickup time + transit.
        earliest = None
        if self.on("transit"):
            if req.get("check_call_eta"):
                earliest = datetime.fromisoformat(req["check_call_eta"])
            else:
                pfac = load["pickup"]["facility"]
                pu = pickup_dt or tms.local(pfac, load["pickup"]["appt"])
                earliest = pu + tms.transit(load["miles"])
            if not self.on("timezone"):
                # wall-clock time carried across without conversion
                pl = earliest.astimezone(tms.tz(load["pickup"]["facility"]))
                earliest = pl.replace(tzinfo=tms.tz(dfac))
        d = load["delivery"]
        own = [d["appt"]] if d.get("appt") else []
        slot, why = self._pick(tms, dfac, d["window_start"], d["window_end"], received, earliest, flags,
                               n_loads=len(loads))
        if slot == "competing":
            return self._handoff("coordinator", "competing_loads", ln, why)
        if slot is None:
            return self._handoff("coordinator", "no_slot_in_window", ln, why)
        if self.on("handoff") and d.get("must_deliver_by") and slot > tms.local(dfac, d["must_deliver_by"]):
            return self._handoff("coordinator", "late_to_receiver", ln,
                                 f"Earliest feasible slot {tms.fmt(dfac, slot)} is after the receiver's "
                                 f"deadline {d['must_deliver_by']}.")
        # 6. Facility reply: accept a counter-offer if the carrier can make it.
        co = fresp.get("counter_offer")
        if co:
            if self.on("reply"):
                cdt = tms.local(dfac, co)
                ok = (earliest is None or cdt >= earliest) and cdt <= tms.local(dfac, d["window_end"])
                if not ok:
                    return self._handoff("coordinator", "counter_offer_infeasible", ln, f"Counter-offer {co} infeasible.")
                slot = cdt
        appts.append(dict(facility=dfac, local=tms.fmt(dfac, slot)))
        if req.get("kind") == "reschedule":
            notify.add("ae")
        return self._book(tms, case, load, appts, dfac, flags, notify)

    # ---- helpers ----
    def _pick(self, tms, fac, ws, we, received, earliest, flags, n_loads=1):
        start = tms.local(fac, ws)
        end = tms.local(fac, we)
        notice = timedelta(hours=tms.facilities[fac]["notice_hours"])
        slots = tms.slots(fac, start, respect_calendar=self.on("calendar"))
        slots = [s for s in slots if s >= start]
        if earliest is not None:
            slots = [s for s in slots if s >= earliest]
        before_notice = slots[0] if slots else None
        if self.on("notice"):
            slots = [s for s in slots if s >= received + notice]
        inside = [s for s in slots if s <= end] if self.on("window") else slots
        if self.on("handoff") and n_loads > 1 and len(inside) < n_loads:
            return "competing", f"{n_loads} loads, {len(inside)} slot(s) left at {fac}."
        if not inside:
            if self.on("handoff"):
                opts = ", ".join(tms.fmt(fac, s) for s in slots[:3])
                return None, f"No slot inside the window at {fac}; options outside it: {opts}."
            inside = slots
            if not inside:
                return None, "No slots at all."
        slot = inside[0]
        if before_notice is not None and slot != before_notice and self.on("notice"):
            flags.add("notice")
        if self.on("calendar"):
            d = start.date()
            while d < slot.date():
                if d.isoformat() in tms.facilities[fac]["holidays"]:
                    flags.add("holiday")
                d += timedelta(days=1)
        return slot, ""

    def _book(self, tms, case, load, appts, fac, flags, notify):
        channel = tms.facilities[fac]["channel"]
        attempts = [channel]
        errors = case.get("facility_response", {}).get("portal_errors", 0)
        if channel == "portal" and errors:
            if not self.on("fallback"):
                return self._handoff("coordinator", "portal_error", load["load_no"], "Portal error on booking.")
            attempts.append("portal")          # retry once
            if errors >= 2:
                attempts.append("email")        # then fall back to email
                channel = "email"
        if load["carrier_assigned"]:
            notify.add("carrier")
        if flags:
            notify.add("ae")
        last = appts[-1]
        return dict(action="book", load=load["load_no"], appointments=appts, channel=channel, attempts=attempts,
                    confirmation=tms.confirmation(last["facility"], last["local"]), notify=sorted(notify), flags=sorted(flags),
                    log=f"Booked {', '.join(a['facility'] + ' ' + a['local'] for a in appts)} via {channel}"
                        + (f"; flags: {', '.join(sorted(flags))}" if flags else "") + ".")

    @staticmethod
    def _handoff(to, reason, load, why):
        return dict(action="handoff", to=to, reason=reason, load=load, log=why)


class NaiveAgent(SpecAgent):
    """'Always book': the reference agent with every check switched off."""
    name = "naive"

    def __init__(self):
        super().__init__(off=CHECKS)
