# Shift Supervisor on Desk (alpha.36 V1), report only

Site fresh.local, 6 Oct 2026. User `nadi.w0.manager@example.invalid` (HR-EMP-00008, roles: Shift Supervisor, Leave Approver, Employee, Desk User).
Team = HR-EMP-00008, 00009, 00027. Non-team = any other employee (e.g. 00003, 00001).
Every cell is the real answer from `frappe.set_user(SUP)` + the call named. Writes ran inside a savepoint and were rolled back (verified: HR-SHA-26-09-00030 still Active, docstatus 1).
Scripts: /tmp/v1/probe.py (has_permission, get_list), /tmp/v1/api.py (whitelisted APIs). Perm cells = `frappe.has_permission(dt, ptype, doc)` on a real row.
Verdict: OK / GAP / LEAK / UNCLEAR vs docs/glass/ACCESS-MATRIX.md and CHANGELOG alpha.28/33/34.

## Row-level table (team row / non-team row)

| Doctype | get_list (visible / total) | read | write | create | delete | submit | Verdict |
|---|---|---|---|---|---|---|---|
| Employee Checkin | 4 / 30 | team yes / non-team no | no / no | no / no | no / no | no / no | OK (view only, alpha.33) |
| Attendance | 16 / 66 | yes / no | no / no | no / no | no / no | no / no | OK (view only, alpha.33) |
| Shift Assignment | 7 / 20 | yes / no | yes / no | yes / no | no / no (doc-level) | yes / no | OK (rosters team; delete goes via API) |
| Shift Type | 25 / 25 | yes / n.a. | no | no | no | no | UNCLEAR: reads every Shift Type, no company fence |
| Leave Application | 3 / 46 | yes / no | no / no | no / no | no / no | no / no | OK (matrix: manager sees, read only). Doctype-level create = yes (own leave) |
| Attendance Request | 1 / 3 | yes / no | no / no | no / no | no / no | no / no | OK (TEAM_REVIEWED, read only) |
| Shift Request | 1 / 1 | yes / (no non-team row) | no | no | no | no | OK (read; decide is via Approvals page, not tested on Desk) |
| OT Request | 1 / 1 | yes / (no non-team row) | no | no | no | no | UNCLEAR: matrix says a manager can "see + decide" OT; has_permission write/submit = no on Desk. Decision may go via the PWA API (not probed) |
| Remote Checkin Request | 0 / 0 | no rows on site | n/a | doctype create yes | n/a | n/a | UNCLEAR: no data to probe |
| Expense Claim | 1 / 2 | yes / no | no / no | no / no | no / no | no / no | OK (matrix: manager see, read) |

## Whitelisted APIs (savepoint, rolled back)

| Call (as supervisor) | Team employee | Non-team employee | Verdict |
|---|---|---|---|
| roster.get_events(Sep-Oct, company filter Nadi W0 A) | OK, 3 keys | other company (HR-EMP-00012's): OK, 0 events | OK |
| roster.update_shift_assignment(HR-SHA-26-09-00030, "Inactive") / (HR-SHA-26-09-00023) | OK | REFUSED "You are not permitted to roster this employee." | OK |
| roster.delete_shift_assignment(same) | OK (future day, no punches) | REFUSED same message | OK |
| roster.preview_shift_change(emp, 2027-01-05, [shift]) | REFUSED "Only HR can change a person's shift from a date." | REFUSED "not permitted to roster" | UNCLEAR (alpha.28 says supervisors "change" team shifts; this bulk change is HR only) |
| roster.change_shift_from(same args) | REFUSED "Only HR can change..." | REFUSED not permitted | UNCLEAR (same) |
| attendance_fix_day.fix_days(emp, 2026-09-10, 2026-09-10, dry_run=True) | REFUSED PermissionError | REFUSED PermissionError | OK (HR only by design) |
| frappe.delete_doc("Shift Assignment", team row) direct | REFUSED PermissionError | n/a | OK (supervisors go through the API; alpha.34) |
| doc.save() of status on a team Shift Assignment direct | OK | n/a | OK |

Not run (no brief cell needed a result beyond the above): swap_shift, break_shift, remove_shift_day, change_shift_day, insert_shift, create_shift_schedule_assignment.

## GAP lines
- None proven. Shift Type read-all and OT decide-on-Desk are UNCLEAR, not GAP.

## LEAK lines
- None. Shift Type: all 25 visible to the supervisor (re-checked by the orchestrator: get_list as the supervisor
  returns 25 of 25). Shift Type has no company field (meta: only holiday_list), so there is nothing to fence by:
  it is a shared catalogue of shift times with no personal data, and supervisors need it to roster. OK, not a leak.

## UNCLEAR lines (need owner ruling)
- roster.change_shift_from / preview_shift_change refused for supervisors: hrms/api/roster.py:560 and :598 ("Only HR can change a person's shift from a date.").
- OT Request decision on Desk for a manager: no write/submit via has_permission; matrix row "Overtime ... Manager (direct) see + decide" relies on ot_row_scope (hrms/overrides/ot_row_scope.py:52,90) and the PWA approval API, which this probe did not exercise.
- Remote Checkin Request: zero rows on fresh.local.
