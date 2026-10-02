# Shift Supervisor: Nadi tile says "No permission for Page" (Fauzi, 2 Oct 2026)

## FLOW
Desk launcher -> frappe desktop_icon.get_desktop_icons filters each tile by the icon's own Has Role rows
-> "Shift & Attendance" tile HR-only -> Nadi app tile has no children -> opens its own link /desk/people
-> no "people" workspace (upstream renamed to HR Setup) -> router falls to Page "people" -> Page read is System Manager only -> error.
Fix: tile roles + Shift Supervisor (JSON + patch let_shift_supervisor_open_nadi_tile); app_home / add_to_apps_screen / Nadi icon link -> /desk/shift-&-attendance.

## MOCKUP: NOT NEEDED (no new screen; an existing tile becomes visible to one more role)

## EXPECTED OUTPUT
- Shift Supervisor with an Employee record: Desk shows Nadi -> Shift & Attendance; app route /desk/shift-&-attendance.
- HR: unchanged (tile already theirs). Plain employee: tile still hidden.
- Patch idempotent (ran twice on fresh.local).

APPROVED: owner, 2 Oct 2026 — "urgent fix ... shift supervisor should able to use roster and view roster page!"
