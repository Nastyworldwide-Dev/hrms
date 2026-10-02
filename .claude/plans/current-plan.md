# Shift Supervisor on Desk: their team's attendance and clock-ins, read only (owner, 2 Oct 2026)

Owner: "shift supervisor role, can use desk, as usual, but limited to only attendance, clock in
records ... only can view their own people under them". Answers: VIEW ONLY; team = the roster's
own list (self + Reports To = them, hrms.hr.utils.rostered_employees); Desk shows ONLY Shift &
Attendance.

## FLOW
1. Row fence (hrms/overrides/employee_owned_row_scope.py) — Attendance and Employee Checkin
   already route through it (hooks.py permission_query_conditions + has_permission). Add a
   READ-ONLY team scope for a Shift Supervisor: list + document read admit rows whose employee
   is in rostered_employees(user). Write/create/submit/delete: unchanged.
2. Role permission (patch, idempotent): Shift Supervisor gets read + report on Attendance and
   Employee Checkin, incl. Employee Checkin permlevel 1 read. No write/create/submit/export.
3. Desk: Shift & Attendance sidebar shows a supervisor only what they can open (Frappe hides
   links the user cannot read). Other Nadi tiles are already HR-only. Check as the persona.
4. Monthly Attendance Sheet is already fenced to the team (report_scope). Other reports stay
   HR-only.

## MOCKUP: NOT NEEDED (no new screen; existing Desk lists/forms, read only, team rows only)

## EXPECTED OUTPUT
- A Shift Supervisor on Desk -> Nadi -> Shift & Attendance: Attendance and Employee Checkin
  lists show only them + their direct reports; forms read only; no New/Edit/Submit.
- A stranger's Attendance / Checkin by URL: "not permitted".
- Plain Employee and HR: unchanged. Nadi PWA: unchanged.

## TESTS
- row scope: supervisor reads a report's Attendance + Checkin; refused a stranger's; refused
  write on a report's row; plain employee unchanged — red first.
- patch idempotent; persona boot check on fresh.local.

## RISK
Permissions (read only, team only). Pay untouched (no write).

APPROVED: owner, 2 Oct 2026 — "go" (view only, roster team, Desk Shift & Attendance only).
