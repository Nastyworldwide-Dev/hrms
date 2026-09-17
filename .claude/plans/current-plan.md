# PLAN — the geofence allowance has a cliff in it

Owner, 17 Sep 2026: "i still get report regarding geofence, some experience had
to remote request despite in the area for check in. accuracy problems. or idk.
do check."

## Measured, not guessed

Run against the real function, same person, standing 80 m from the centre of a
50 m fence:

    accuracy 249 m -> ALLOWED
    accuracy 250 m -> ALLOWED
    accuracy 251 m -> require_remote (imprecise_location)

One metre of extra reported error costs 250 metres of tolerance.

## Why

The allowance a reading buys was `accuracy`, up to `ACCURACY_ALLOWANCE_CAP_M`
(250 m), and **zero** beyond it. Between that cap and
`POINT_ESTIMATE_TRUST_CAP_M` (2000 m) the code already treats the device's own
estimate as meaningful — it says so, and it allows a point that lands inside
the radius — but it gave that same estimate no tolerance at all the moment the
point landed a few metres outside.

Trusted when it helps, discarded when it does not. A phone indoors reporting
400 m of error, with its point estimate 80 m from the office centre, was sent
to its approver; the error bar that would have covered the whole building
bought nothing.

## FLOW

`hrms/utils/geofence.py::evaluate_geofence`, and its mirror
`frontend/src/utils/geolocation.js::previewGeofence` (a property test asserts
the two agree case for case, and it caught the drift immediately):

    allowance = 0                       when accuracy > 2000 m   (unchanged)
    allowance = min(accuracy, 250 m)    otherwise                (was: accuracy
                                                                  under 250,
                                                                  zero over it)

Past the trust cap nothing changes: an IP-level fix places nobody, and landing
inside a fence by a provider's centroid is luck, not presence — still
`imprecise_location`, still a throw in strict mode.

MOCKUP: NOT NEEDED (no screen, control or copy changes. The employee sees the
same check-in sheet; it stops sending them to an approver they do not need.)

## EXPECTED OUTPUT

* The reported case: allowed at 251 m of error, as it already was at 250 m.
* The allowance never shrinks as a reading gets worse (monotonic).
* A kilometre of error still widens a fence by at most 250 m.
* A sharp reading well outside is still outside.
* A reading past 2000 m still places nobody, even when it lands inside.
* Strict mode still throws exactly where lenient routes to approval.

## The trade-off, stated

This is more permissive than today for readings between 250 m and 2000 m of
error: such a reading now buys up to 250 m of tolerance instead of none. In
lenient mode that means fewer remote approvals for people who are where they
say they are — the reported complaint. In strict mode it means fewer refusals.
It cannot be used to clear a fence from far away: the allowance is capped, and
anyone beyond radius + 250 m is still outside.

## Pipeline Summary

owner report -> measured on the real function -> this plan -> red tests first
(7 cases: the exact metre it flipped, monotonicity, the cap still capping, and
four that pin what must not change) -> the change on both sides -> the
cross-language parity property test -> commit with the family ledger ->
hook-dispatched review -> push -> the owner releases. No schema change, no
patch, no data repair; the next punch is decided by the new rule.
