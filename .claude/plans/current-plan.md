# Shift Supervisor can open the roster (Fahmie, 29 Sep 2026)

1. Patch let_shift_supervisor_open_roster: Shift Supervisor on the "Shift & Attendance" workspace + read on Branch and Designation.
2. (next commit) One "who a supervisor sees" rule: direct reports + same Branch as the supervisor's own Employee record; roster uses it.
3. (next commit) Monthly Attendance Sheet uses that rule, then opens to Shift Supervisor.

## FLOW
patches.txt -> let_shift_supervisor_open_roster.execute -> add_permission/update_permission_property (Branch, Designation read) -> Workspace "Shift & Attendance".roles += Shift Supervisor
Desk /desk/shift-&-attendance -> desk_page.getpage -> Workspace.is_permitted (roles) ; roster MonthViewHeader -> frappe.client.get_list Branch/Designation

## MOCKUP: NOT NEEDED (permission patch, no UI change; the existing Desk workspace and roster now open)

## EXPECTED OUTPUT
- Shift Supervisor runs Monthly Attendance Sheet: only self + direct reports; strangers never; no role = refused.
- Shift Supervisor opens Desk "Shift & Attendance": no "No permission for Page".
- /hr/roster: no "Insufficient Permission for Branch / Designation" toasts.
- Branch and Designation are read-only for the role; roster writes stay fenced to own team.

Owner ruling 29 Sep 2026 ("ok"): option A — a supervisor's team = direct reports only (not branch-wide).
Step 3 detail: report_scope.report_employees() = None for HR, [self + direct reports] for Shift Supervisor, [] otherwise; Monthly Attendance Sheet narrows its population with it; patch adds Has Role (db_insert — standard Report refuses save outside developer mode).

APPROVED: owner, 29 Sep 2026 — "go" (after "i think the field?"), then "ok" to option A.
