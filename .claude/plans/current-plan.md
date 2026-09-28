# Plan — 28 Sep 2026: check in at more than one site (HR request)

## Owner answers (28 Sep 2026)
- Meaning: several sites per person (e.g. Damansara AND Shah Alam; inside either = accepted).
- Where: on the Employee record, set once.
- Outside ALL sites: same rule as today (normal -> approver; strict -> refused). The tickbox only ADDS sites.
- Each check-in records WHICH site it matched, shown in reports.

## What exists today (read, not guessed)
- One site per person: Employee.shift_location (or the Shift Assignment's own).
- ONE resolver, `effective_shift_location()` in hrms/utils/geofence.py, feeds three readers:
  1. the enforcing insert — hrms/overrides/employee_checkin_override.py validate_distance_from_shift_location
  2. the strict preflight — hrms/api/geofence.py check_geofence
  3. the PWA map pin — hrms/api/geofence.py get_active_shift_location
- Decision rule: `evaluate_geofence()` (pure), per site.
- Approval request names `nearest_shift_location` (employee_checkin_after_insert.py) -> Out of Radius report.
- Employee.shift_location ALSO drives automatic Shift Assignment rules (hrms/hr/shift_rules.py).

## The change
Desk, Employee record (Attendance section, under Shift Location):
- [ ] **Can check in at more than one site** (tickbox)
- **Other sites** — pick one or more Shift Locations (shows only when ticked)

Rule, in ONE place (hrms/utils/geofence.py):
- `employee_sites(employee, assignment)` = the effective site (unchanged) + the other sites when ticked.
- `evaluate_sites(...)` runs the existing `evaluate_geofence` against each site:
  - any site accepts -> accepted, and that site is recorded;
  - none accept -> today's decision, measured against the NEAREST site (normal -> approver, strict -> refused).
- All three readers call it, so the screen that warns and the code that enforces cannot disagree.

Record: new read-only **Checked in at** (Shift Location) on Employee Checkin; shown in the check-in list and the Out of Radius report. The approval request names the nearest site.

## Kept apart on purpose (blast area)
- Automatic shift rules keep reading ONLY the main Shift Location. The other sites never change anyone's shift.
- Tickbox off, or no other sites = exactly today's behaviour (proved by test).
- A "free location" site still means "anywhere" — unchanged.
- Hub sync: Employee is a mirrored doctype. I check whether the new fields would be overwritten or dropped by a sync before shipping; if they would, I say so and stop.

## FLOW
Employee (tick + Other sites) -> employee_sites() -> evaluate_sites() -> {check-in insert, strict preflight, PWA map} -> Employee Checkin.checked_in_at -> Out of Radius report / check-in list.

## MOCKUP: NOT NEEDED (Desk form fields in the standard Frappe layout; the owner confirms on the real form after deploy)

## EXPECTED OUTPUT
- HR ticks the box on Ali, picks Shah Alam. Ali checks in at Shah Alam -> accepted, "Checked in at: Shah Alam".
- Ali checks in 5 km from both -> normal: goes to his approver, naming the nearest site; strict: refused.
- Anyone without the tickbox: nothing changes.
- The PWA map shows the nearest of his sites.

## Tests (red first)
- Pure: accepted by the second site; outside both -> nearest-site decision; tickbox off = today.
- Live on the dev site: two sites, one employee, three check-ins (site 1, site 2, far) — then synthetic rows deleted.
- Invariant: shift rules never read the other sites.

## Ship
One slice per commit (rule + tests, fields + patch, reports/PWA), review each, one version bump (alpha.16), release with scripts/release.sh. You deploy.

## F. Sheets: scrolling inside a sheet moved the sheet (senior report, 28 Sep 2026)
Root cause: Ionic's sheet gesture yields only to a drag inside `ion-content`; GModal's scroller was a plain div, so every drag moved the sheet. Fix: GModal wraps its content in ion-content (head stays outside, still drags). One file + CSS; all 33 sheet screens.
FLOW: GModal -> ion-modal(sheet) -> .g-sheet (column) -> head | ion-content.g-sheet__content -> body slot.
MOCKUP: NOT NEEDED (no visual change intended; iOS gate's sheet-consistency and sheet-shift audits verify look and motion).
EXPECTED OUTPUT: in a sheet, dragging the list scrolls it and never moves or closes the sheet; the grabber/title bar still drags; short sheets stay short.
